import json
import sqlite3
import sqlparse
from sqlparse import tokens
import base64

import Search

# For debugging / demonstration
print_sql = True

class Cell:
  CONTENT_PROP = "content"
  KEY_LIST_PROP = "key_list"
  SEARCH_BLOB_PROP = "search_blob"

  def __init__(self, props):
    self.content = None if self.CONTENT_PROP not in props else props[self.CONTENT_PROP]
    self.key_list = props[self.KEY_LIST_PROP]
    self.search_blob = None if self.SEARCH_BLOB_PROP not in props else props[self.SEARCH_BLOB_PROP]
    
  @staticmethod
  def from_json(json_str):
    return Cell(json.loads(json_str))

  def to_json(self, metadata=False, pub_key=None, strip_search=False):
    d = {}
    if not metadata:
      d[self.CONTENT_PROP] = self.content

    if pub_key is None:
      d[self.KEY_LIST_PROP] = self.key_list
    else:
      d[self.KEY_LIST_PROP] = [x for x in self.key_list if x[0] == pub_key]
    
    if not strip_search and not metadata and self.search_blob is not None:
      d[self.SEARCH_BLOB_PROP] = self.search_blob
    
    return json.dumps(d)

  def __str__(self):
    return "Cell({}, {})".format(self.content, self.key_list)

class LockdownConnection:
  def __init__(self, db_file, *args, **kwargs):
    self.conn = sqlite3.connect(db_file, *args, **kwargs)
    self.__fetch_table_names()
    self.__fetch_encrypted_columns()
  
  def sqlite_conn(self):
    return self.conn

  def close(self):
    self.conn.close()

  def cursor(self):
    return LockdownCursor(self)

  def __fetch_table_names(self):
    cur = self.conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    self.tables = set(x[0] for x in cur.fetchall() if x[0] != "sqlite_sequence")

    if "Lockdown_Schema" not in self.tables:
      cur.execute("CREATE TABLE Lockdown_Schema (table_name TEXT, encrypted_columns TEXT)")
      self.conn.commit()
      self.tables.add("Lockdown_Schema")
    
    new_tables = set()
    for table in self.tables:
      if table.startswith("Lockdown_"):
        continue
      if "Lockdown_{}".format(table) not in self.tables:
        cur.execute("CREATE TABLE Lockdown_{} (id INTEGER, column_name TEXT, pub_key TEXT)".format(table))
        self.conn.commit()
        new_tables.add("Lockdown_{}".format(table))
      if "Lockdown_Search_{}".format(table) not in self.tables:
        cur.execute("CREATE TABLE Lockdown_Search_{} (id INTEGER, column_name TEXT, search_blob TEXT)".format(table))
        self.conn.commit()
        new_tables.add("Lockdown_Search_{}".format(table))
      
    self.tables = self.tables.union(new_tables)

  def __fetch_encrypted_columns(self):
    cur = self.conn.cursor()
    cur.execute("SELECT * FROM Lockdown_Schema")
    self.encrypted_columns = {}
    for table, columns in cur.fetchall():
      self.encrypted_columns[table] = set(columns.split(","))

class QueryType:
  NONE=0
  STANDARD=1
  REWRITTEN_SELECT=2
  REWRITTEN_INSERT=3

class LockdownCursor:
  def __init__(self, ld_conn):
    self.ld_conn = ld_conn

    self.cursor = self.ld_conn.sqlite_conn().cursor()
    real_exec = self.cursor.execute

    def hijack_execute(*args, **kwargs):
      print(args[0])
      real_exec(*args, **kwargs)

    class Wrapper(object):
      def __init__(self, obj):
        self._wrapped_obj = obj
      def __getattr__(self, attr):
        if attr == "execute":
          return hijack_execute
        if attr in self.__dict__:
            return getattr(self, attr)
        return getattr(self._wrapped_obj, attr)
    
    if print_sql:
      self.cursor = Wrapper(self.cursor)

    self.last_query_type = QueryType.NONE
    self.last_select_table = None
    self.last_select_columns = None

  def __execute_select(self, sql, params, pub_key, search_keys):
    parsed = sqlparse.parse(sql)[0]
    col_names = []
    is_wildcard = False

    for t in parsed.tokens:
      if t.ttype == tokens.Keyword:
        break
      
      if type(t) == sqlparse.sql.IdentifierList:
        col_names = [x.value for x in t.get_identifiers()]
        break
      
      if type(t) == sqlparse.sql.Identifier:
        col_names = [t.value]
        break
      
      if t.ttype == tokens.Wildcard:
        is_wildcard = True
        break

    table_name = None
    saw_from = False
    for t in parsed.tokens:
      if saw_from and type(t) == sqlparse.sql.Identifier:
        table_name = t.value
        break

      if t.ttype == tokens.Keyword and t.value.lower() == "from":
        saw_from = True

    if table_name not in self.ld_conn.tables:
      raise ValueError("Table {} does not exist".format(table_name))

    if is_wildcard:
      # TODO: Should we calculate this at startup?
      cur = self.ld_conn.sqlite_conn().cursor()
      # table_name should be whitelisted
      cur.execute("PRAGMA table_info({})".format(table_name))
      col_names = [x[1] for x in cur.fetchall()]

    self.last_query_type = QueryType.REWRITTEN_SELECT
    self.last_query_table = table_name
    self.last_query_columns = col_names

    # If there is a LIKE, we need to disable it (by replacing with LIKE '%%')
    # When no search keys provided, select row id and column content (to be used in metadata fetch)
    # If search keys provided, select row id and search blob, perform search, then select final ids

    # Disable LIKE if exists, and flag it
    is_search = False
    search_column = None

    for t in parsed.tokens:
      if type(t) == sqlparse.sql.Where:
        last_identifier = ""
        found_like = False
        for where_t in t.tokens:
          if type(where_t) == sqlparse.sql.Identifier:
            last_identifier = where_t.value

          # Only flag a LIKE if column is encrypted
          if (last_identifier in self.ld_conn.encrypted_columns[table_name] and
              where_t.ttype == tokens.Keyword and where_t.value.lower() == "like"):
            found_like = True
            is_search = True
            search_column = last_identifier

          if where_t.ttype == tokens.Literal.String.Single and found_like:
            where_t.value = "'%%'"
            break

    # Snapshot query here before we insert pub keys (for search to restore)
    snapshot = str(parsed)

    # Insert pub key matching
    # Matching condition
    def insert_cond(cond_sql):
      cond_parsed = sqlparse.parse(cond_sql)[0]

      # Create WHERE clause if it doesn't exist, else concatenate condition to AND
      found_where = False
      for t in parsed.tokens:
        if type(t) == sqlparse.sql.Where:
          found_where = True
          t.tokens.extend(sqlparse.parse(" AND ")[0].tokens)
          t.tokens.extend(cond_parsed.tokens)

      if not found_where:
        # Historical artifact found here! Congratulations
        parsed.tokens.append(sqlparse.sql.Token(sqlparse.tokens.Whitespace, ' '))
        parsed.tokens.append(sqlparse.sql.Where(sqlparse.sql.TokenList([
          sqlparse.sql.Token(sqlparse.tokens.Keyword, 'WHERE'), 
          sqlparse.sql.Token(sqlparse.tokens.Whitespace, ' '), 
          *cond_parsed.tokens
        ])))

    cond_sql = "id IN (SELECT id FROM Lockdown_{} WHERE pub_key=(?)) ".format(table_name)
    insert_cond(cond_sql)

    if is_search:
      for i, t in enumerate(parsed.tokens):
        if type(t) == sqlparse.sql.IdentifierList or type(t) == sqlparse.sql.Identifier or t.ttype == tokens.Wildcard or t.ttype == tokens.Keyword:
          if search_keys is None:
            # For metadata step, we want to first replace the result columns with id, column
            parsed.tokens[i] = sqlparse.parse("id, {}".format(search_column))[0].tokens[0]
            self.last_query_columns = ["id", search_column]
            col_names = self.last_query_columns
          else:
            # For search step we want to replace with id, search_blob
            parsed.tokens[i] = sqlparse.parse("id, search_blob")[0].tokens[0]
          break

    # For metadata step, do nothing now (will return id, column metadata when fetchall is called)
    # For search step, run query ahead of time, find relevant ids, and then run original query (selecting those ids)
    if is_search and search_keys is not None:
      saw_from = False
      for i, t in enumerate(parsed.tokens):
        if saw_from and type(t) == sqlparse.sql.Identifier:
          parsed.tokens[i] = sqlparse.parse("({} NATURAL JOIN Lockdown_Search_{})".format(table_name, table_name))[0].tokens[0]
          break

        if t.ttype == tokens.Keyword and t.value.lower() == "from":
          saw_from = True
      
      self.cursor.execute(str(parsed), [*params, pub_key])
      rows = self.cursor.fetchall()

      found_ids = []
      for row_id, search_blob_json in rows:
        search_blob = [base64.b64decode(x) for x in json.loads(search_blob_json)]
        search_key = [base64.b64decode(x) for x in search_keys[str(row_id)]]

        if Search.search(search_blob, search_key[0], search_key[1]):
          found_ids.append(row_id)

      # Reset query to use different condition insert
      parsed = sqlparse.parse(snapshot)[0]
      insert_cond("id IN ({}) ".format(",".join(str(x) for x in found_ids)))
  
    # TODO: investigate if this is the right position to put pub key, can the match_sql ever appear before any param?
    # TODO: We could just use a named parameter instead of a question mark? https://stackoverflow.com/questions/29686112/named-parameters-in-python-sqlite-query

    if is_search and search_keys is not None:
      # Don't insert pub key anymore, we have specific ids
      self.cursor.execute(str(parsed), params)
    else:
      self.cursor.execute(str(parsed), [*params, pub_key])

  def __execute_insert(self, sql, params):
    parsed = sqlparse.parse(sql)[0]
    insert_columns = []
    table_name = None
    saw_into = False
    for t in parsed.tokens:
      if saw_into and type(t) == sqlparse.sql.Function:
        insert_columns = [x.value for x in t.get_parameters()]
        table_name = t.get_name()
        break

      if t.ttype == tokens.Keyword and t.value.lower() == "into":
        saw_into = True

    if not saw_into:
      raise ValueError("INTO not found for INSERT statement")

    if len(insert_columns) == 0:
      raise ValueError("Columns to INSERT should be explicit (due to autoincrement)")

    for i, p in enumerate(params):
      if type(p) == Cell and insert_columns[i] not in self.ld_conn.encrypted_columns[table_name]:
        raise ValueError("Column {} not marked as encrypted in Lockdown_Schema, but passed a Cell".format(insert_columns[i]))
    
    self.last_query_type = QueryType.REWRITTEN_INSERT
    self.last_query_table = table_name
    self.last_query_columns = insert_columns

    self.cursor.execute(str(parsed), [x.to_json(strip_search=True) if type(x) == Cell else x for x in params])

    row_id = self.cursor.lastrowid
    
    for i, p in enumerate(params):
      if type(p) != Cell:
        continue

      for pub_key, enc_sym in p.key_list:
        # TODO: id should be a foreign key reference that will delete
        self.cursor.execute(
          "INSERT INTO Lockdown_{} (id, column_name, pub_key) VALUES (?, ?, ?)".format(table_name), 
          (row_id, insert_columns[i], pub_key)
        )
      
      if p.search_blob is not None:
        # TODO: id should be a foreign key reference that will delete
        self.cursor.execute(
          "INSERT INTO Lockdown_Search_{} (id, column_name, search_blob) VALUES (?, ?, ?)".format(table_name), 
          (row_id, insert_columns[i], json.dumps(p.search_blob))
        )
    
    self.ld_conn.sqlite_conn().commit()

  # TODO: investigate making pub_key a list of pub keys to get all those keys own
  def execute(self, sql, params=tuple(), pub_key=None, search_keys=None):
    parsed = sqlparse.parse(sql)[0]

    self.last_query_type = QueryType.NONE
    
    if parsed.tokens[0].ttype != tokens.DML:
      raise ValueError('Unsupported operation')

    op_type = parsed.tokens[0].value

    if op_type == "SELECT" and pub_key is not None:
      self.__execute_select(sql, params, pub_key, search_keys)
    elif op_type == "INSERT":
      self.__execute_insert(sql, params)
    else:
      self.cursor.execute(sql, params)
  
  # TODO: Consider implementing fetchone, etc

  def fetchall(self, metadata=False, pub_key=None):
    res = self.cursor.fetchall()

    # Strip cell contents if asked to
    if self.last_query_type == QueryType.REWRITTEN_SELECT:
      enc_cols = self.ld_conn.encrypted_columns[self.last_query_table]
      for i, row in enumerate(res):
        mut_row = list(row)
        for j in range(len(mut_row)):
          if self.last_query_columns[j] in enc_cols:
            mut_row[j] = Cell.from_json(mut_row[j]).to_json(metadata=metadata, pub_key=pub_key)
        res[i] = tuple(mut_row)

    return res