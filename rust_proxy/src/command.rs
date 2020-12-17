use async_std::io::ReadExt;
use async_std::net::TcpStream;
use async_std::prelude::*;
use async_std::sync::{Arc, Mutex};
use async_trait::async_trait;
use bincode;
use byteorder::{ByteOrder, LittleEndian};
use crate::BoxedErrorResult;
use crate::constants::HEADER_SIZE;
use crate::server::SharedDB;
use rusqlite;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::convert::{TryFrom, TryInto};
use std::error::Error;

// impl TryFrom<rusqlite::Row> for HashMap<String, serde_json::Value> {
//     type Error = Box<dyn Error + Send + Sync>;
    
//     fn try_from(row: rusqlite::Row) -> BoxedErrorResult<Self> {
//         let out = HashMap::new();
//         for column_name in row.column_names() {
//             let idx = row.column_index(column_name);
//             let item: serde_json::Value = row.get(idx)?;
//             out.insert(column_name.into(), item);
//         }
//         Ok(out)
//     }
// }

// /// Serialize JSON `Value` to text.
// impl ToSql for Value {
//     fn to_sql(&self) -> rusqlite::Result<ToSqlOutput<'_>> {
//         Ok(ToSqlOutput::from(serde_json::to_string(self).unwrap()))
//     }
// }

// /// Deserialize text/blob to JSON `Value`.
// impl FromSql for Value {
//     fn column_result(value: ValueRef<'_>) -> FromSqlResult<Self> {
//         match value {
//             ValueRef::Text(s) => serde_json::from_slice(s),
//             ValueRef::Blob(b) => serde_json::from_slice(b),
//             _ => return Err(FromSqlError::InvalidType),
//         }
//         .map_err(|err| FromSqlError::Other(Box::new(err)))
//     }
// }

// Might wanna allow more complex types as values?
type SqlRow = HashMap<String, String>;


trait GenMap {
    fn gen_map(&self) -> BoxedErrorResult<SqlRow>;
}

impl GenMap for rusqlite::Row<'_> {
    fn gen_map(&self) -> BoxedErrorResult<SqlRow> {
        let mut out = HashMap::new();
        for column_name in self.column_names() {
            let idx = self.column_index(column_name).unwrap();
            let item = self.get_unwrap(idx);
            out.insert(column_name.into(), item);
        }
        Ok(out)        
    }
}

// TODO: Probably make this a protobuf eventually
// command_type should be either 'QUERY' or 'EXECUTE'
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Command {
    pub command_type: String,
    pub command: String,
    pub params: Vec<String>
}

impl Command {
    pub async fn execute(self, db: &mut SharedDB) -> BoxedErrorResult<Response> {
        match self.command_type.to_uppercase().as_str() {
            "QUERY" => {
                let mut locked_db = db.lock().await;
                let mut stmt = locked_db.prepare(&self.command)?;
                let mut rows = stmt.query(&self.params)?;
                let mut data = Vec::new();
                while let Ok(Some(row)) = rows.next() {
                    let item_json = row.gen_map()?;
                    data.push(item_json);
                }
                Ok(Response::new("OK".into(), format!("Returned {} rows of data", data.len()),data))
            },
            "EXECUTE" => {
                let num_changed = db.lock().await.execute(&self.command, &self.params)?;
                Ok(Response::new("OK".into(), format!("{} rows changed", num_changed), vec![]))
            },
            _ => Err(format!("Invalid command_type found: {}", self.command_type).into())
        }
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Response {
    pub status: String,
    pub result: String,
    pub data: Vec<SqlRow>
}

impl Response {
    fn new(status: String, result: String, data: Vec<SqlRow>) -> Self {
        Response {
            status: status,
            result: result,
            data: data
        }
    }
}

// TODO: Make these a blanket implementation, but that is haaaard
#[async_trait]
pub trait ReadWriteCommand {
    async fn try_read_command(&mut self) -> BoxedErrorResult<Command>;
    async fn try_write_command(&mut self, command: &Command) -> BoxedErrorResult<()>;
}

#[async_trait]
impl ReadWriteCommand for TcpStream {
    async fn try_read_command(&mut self) -> BoxedErrorResult<Command> {
        // Parse the header
        let mut header: Vec<u8> = vec![0; HEADER_SIZE];
        self.read_exact(&mut header).await?;
        let buf_size: usize = u32::from_le_bytes(header[..HEADER_SIZE].try_into()?) as usize;
        println!("found buf_size of {}", buf_size);
        // Receive the full message - TODO: Some assertions on the buf_size before creating the vec?
        let mut buf: Vec<u8> = vec![0; buf_size];
        self.read_exact(&mut buf).await?;
        // Deserialize the command struct
        let command = serde_json::from_slice(&buf)?;
        Ok(command)
    }
    async fn try_write_command(&mut self, command: &Command) -> BoxedErrorResult<()> {
        let json = serde_json::to_string(command)?;
        let serialized = json.as_bytes();
        let mut le_header = [0u8; 4];
        LittleEndian::write_u32(&mut le_header, serialized.len() as u32);
        self.write_all(&le_header).await?;
        self.write_all(&serialized).await?;
        Ok(())
    }
    
}

#[async_trait]
pub trait ReadWriteResponse {
    async fn try_read_response(&mut self) -> BoxedErrorResult<Response>;
    async fn try_write_response(&mut self, response: &Response) -> BoxedErrorResult<()>;
}

#[async_trait]
impl ReadWriteResponse for TcpStream {
    async fn try_read_response(&mut self) -> BoxedErrorResult<Response> {
        // Parse the header
        let mut header: Vec<u8> = vec![0; HEADER_SIZE];
        self.read_exact(&mut header).await?;
        let buf_size: usize = u32::from_le_bytes(header[..HEADER_SIZE].try_into()?) as usize;
        println!("found buf_size of {}", buf_size);
        // Receive the full message - TODO: Some assertions on the buf_size before creating the vec?
        let mut buf: Vec<u8> = vec![0; buf_size];
        self.read_exact(&mut buf).await?;
        // Deserialize the response struct
        let response = serde_json::from_slice(&buf)?;
        Ok(response)
    }
    async fn try_write_response(&mut self, response: &Response) -> BoxedErrorResult<()> {
        let json = serde_json::to_string(response)?;
        let serialized = json.as_bytes();
        let mut le_header = [0u8; 4];
        LittleEndian::write_u32(&mut le_header, serialized.len() as u32);
        self.write_all(&le_header).await?;
        self.write_all(&serialized).await?;
        Ok(())
    }
    
}
