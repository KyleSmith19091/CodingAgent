use std::str::FromStr;

use reqwest::{Client, Error};
use serde::Serialize;

#[derive(Clone)]
pub struct Embedder {
    embedder_client: Client,
    embedder_client_url: String,
}

#[derive(Serialize)]
#[serde(untagged)]
pub enum Input<'a> {
    Single(&'a str),
    Multiple(&'a Vec<String>),
}

#[derive(Serialize)]
struct EmbedRequest<'a> {
    inputs: Input<'a>,
}

pub type EmbeddingBatch = Vec<Vec<f32>>;

impl Embedder {
    pub fn new(embedder_url: &str) -> Self {
        let client = Client::new();
        Embedder { 
            embedder_client: client,
            embedder_client_url: String::from_str(embedder_url).unwrap(),
        }
    } 

    pub async fn embed(self: &Self, content: Input<'_>) -> Result<EmbeddingBatch, Error> {
        let response = self.embedder_client
            .post(self.embedder_client_url.clone())
            .json(&EmbedRequest {
                inputs: content,
            })
            .send()
            .await?;

        let embeddings: EmbeddingBatch = response.json().await?;

        return Ok(embeddings);
    }
}