extern crate async_std;
extern crate rusqlite;
mod command;
mod constants;
mod server;
use std::error::Error;


pub type BoxedErrorResult<T> = Result<T, Box<dyn Error + Send + Sync>>;

fn main() -> BoxedErrorResult<()> {
    let addr = "127.0.0.1:7070";
    println!("Listening on {}", addr);
    async_std::task::block_on(server::start_server(addr))?;
    Ok(())
}


