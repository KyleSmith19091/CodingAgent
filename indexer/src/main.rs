use reqwest::{Error};

use crate::{directory_indexer::Indexer, embedder::Embedder, server::{AppState, Server}, vector_store_mongo::VectorStoreMongo};

mod server;
mod directory_indexer;
mod embedder;
mod vector_store;
mod vector_store_mongo;

#[tokio::main]
async fn main() -> Result<(), Error> {
    let port: u16 = 3999;

    // connect to mongodb and construct vector store
    let vector_store = VectorStoreMongo::new("mongodb://localhost:27017", "code", "embedding").await;

    // construct embedder
    let embedder = Embedder::new("http://localhost:9090/embed");

    // construct indexer
    let indexer: Indexer<VectorStoreMongo> = Indexer::new(
        2, 
        embedder, 
        vector_store,
    );
    
    // construct server
    let server = Server::new(AppState{ 
        indexer: indexer 
    });

    // listen for incoming connectios
    println!("listening on port {:?}", port);
    server.listen(port).await;
    Ok(())
}
