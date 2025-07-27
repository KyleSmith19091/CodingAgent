use std::{sync::{Arc, Mutex}};

use axum::{extract::State, routing::{post,get}, Json, Router};
use serde::Deserialize;

use crate::{directory_indexer::Indexer, vector_store::VectorStore};

#[derive(Clone)]
pub struct AppState<T: VectorStore + 'static + Send + Sync + Clone> {
   pub indexer: Indexer<T> 
}

pub struct Server<T: VectorStore + 'static + Send + Sync + Clone> {
    state: AppState<T>
}

impl<T: VectorStore> Server<T>
where T: VectorStore + 'static + Send + Sync + Clone {
    pub fn new(state: AppState<T>) -> Self {
        Self {
            state
        }
    }

    pub async fn listen(self: &Self, port: u16) {
        let app = Router::new()
            .route("/index", post(index_handler))
            .route("/health", get(health))
            .with_state(self.state.clone());

        let listener = tokio::net::TcpListener::bind(format!("0.0.0.0:{:?}", port))
            .await
            .unwrap();

        axum::serve(listener, app).await.unwrap();
    }
}

#[derive(Deserialize)]
pub struct IndexRequest {
    pub directory: String,
}

async fn index_handler<T: VectorStore + Send + Sync + 'static + Clone>(
    State(state): State<AppState<T>>,
    Json(req): Json<IndexRequest>,
) -> Result<&'static str, (axum::http::StatusCode, String)> {
    println!("calling index_handler");
    let mut indexer = state.indexer;
    indexer
        .index_directory(req.directory)
        .await
        .map_err(|err| (axum::http::StatusCode::INTERNAL_SERVER_ERROR, format!("{:?}", err)))?;

    Ok("Indexing complete")
}

async fn health() -> Result<&'static str, (axum::http::StatusCode, String)> {
    Ok("All good")
} 
