use mongodb::{Client, Collection};
use serde::{Deserialize, Serialize};

use crate::vector_store::{EmbeddingFile, VectorStore};

#[derive(Serialize, Deserialize)]
struct EmbeddingDoc {
    embedding: Vec<f32>,
    file: String,
}

#[derive(Clone)]
pub struct VectorStoreMongo {
    collection: Collection<EmbeddingDoc>,
}

impl VectorStoreMongo {
    pub async fn new(connection_uri: &str, database_name: &str, collection_name: &str) -> Self {
        let client = Client::with_uri_str(connection_uri).await.unwrap();
        Self {
            collection: client.database(database_name).collection(collection_name),
        }
    }
}

impl VectorStore for VectorStoreMongo {
    async fn store(self: &Self, embedding: EmbeddingFile) {
        // TODO: Handle the error (just panicking if something goes wrong)
        let _ = self
            .collection
            .insert_one(EmbeddingDoc {
                embedding: embedding.embedding,
                file: embedding.content,
            })
            .await
            .unwrap();
    }

    async fn store_batch(self: &Self, embeddings: Vec<EmbeddingFile>) {
        // TODO: Handle the error (just panicking if something goes wrong)
        let docs = embeddings
            .into_iter()
            .map(|embedding| EmbeddingDoc {
                embedding: embedding.embedding,
                file: embedding.content,
            })
            .collect::<Vec<_>>();
        let _ = self.collection.insert_many(docs).await.unwrap();
    }
}
