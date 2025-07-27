pub struct EmbeddingFile {
    pub embedding: Vec<f32>,
    pub content: String,
}

pub trait VectorStore: Send + Sync + Clone {
    async fn store(self: &Self, embedding: EmbeddingFile);
    fn store_batch(self: &Self, embedding: Vec<EmbeddingFile>) -> impl std::future::Future<Output = ()> + Send;
}