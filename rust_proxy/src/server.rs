use async_std::net::{TcpListener, TcpStream};
use async_std::sync::{Arc, Mutex};
use async_std::stream::StreamExt;
use async_std::task::spawn;
use crate::BoxedErrorResult;
use crate::command::{Command, ReadWriteCommand, ReadWriteResponse};
use crate::constants;
use rusqlite;

pub type SharedDB = Arc<Mutex<rusqlite::Connection>>;

pub async fn start_server(addr: &str) -> BoxedErrorResult<()> {
    let mut db = Arc::new(Mutex::new(start_database()?));
    let server = TcpListener::bind(addr).await?;
    let mut incoming = server.incoming();

    while let Some(stream) = incoming.next().await {
        let connection = stream?;
        println!("Handling connection from {:?}", connection.peer_addr());
        spawn(handle_connection_wrapper(connection, db.clone()));
    }
    Ok(())
}

// TODO: Add a print for the Errs
async fn handle_connection_wrapper(mut connection: TcpStream, mut db: SharedDB) -> BoxedErrorResult<()> {
    match handle_connection(connection, db).await {
        Err(e) => {
            println!("Connection error: {}", e);
            Err(e)
        },
        ok => ok
    }   
}

async fn handle_connection(mut connection: TcpStream, mut db: SharedDB) -> BoxedErrorResult<()> {
    let command = connection.try_read_command().await?;
    let response = command.execute(&mut db).await?;
    connection.try_write_response(&response).await?;
    Ok(())
}

fn start_database() -> BoxedErrorResult<rusqlite::Connection> {
    let db_path = format!("{}/{}", constants::DATA_DIR, "test.db");
    let conn = rusqlite::Connection::open(db_path)?;
    Ok(conn)
}
