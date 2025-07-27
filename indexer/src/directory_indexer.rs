use std::{fs, str::FromStr};

use reqwest::Error;
use walkdir::{DirEntry, Error as DirError, WalkDir};

use crate::{
    embedder::{Embedder, Input},
    vector_store::{EmbeddingFile, VectorStore},
};

#[derive(Clone)]
pub struct Indexer<T: VectorStore> {
    embedder: Embedder,
    vector_store: T,
    batch_size: usize,
}

struct BatchEntry {
    file_content: String,
    file_path: String,
}

impl<T: VectorStore> Indexer<T> {
    pub fn new(
        batch_size: usize,
        embedder: Embedder,
        vector_store: T,
    ) -> Self {
        Self {
            embedder: embedder,
            vector_store: vector_store,
            batch_size: batch_size,
        }
    }

    fn should_index(self: &Self, entry: &DirEntry, file_name: &str) -> bool {
        if !entry.file_type().is_file() {
            return false;
        }

        if !file_name.ends_with(".go") {
            return false;
        }

        if file_name.ends_with(".pb.go") {
            return false;
        }

        return true;
    }

    pub async fn index_directory(self: &mut Self, directory: String) -> Result<(), Error> {
        let mut batch: Vec<BatchEntry> = Vec::new();
        for entry in WalkDir::new(directory).into_iter() {
            match entry {
                Ok(dir_entry) => {
                    let file_name = dir_entry.file_name().to_str().unwrap_or_default();

                    if self.should_index(&dir_entry, file_name) {
                        // append to file content to batch
                        batch.push(BatchEntry {
                            file_content: fs::read_to_string(dir_entry.path()).unwrap(),
                            file_path: String::from_str(dir_entry.path().to_str().unwrap())
                                .unwrap(),
                        });
                    }

                    // if we have not accumulated enough entries for a batch continue
                    if batch.len() != self.batch_size {
                        continue;
                    }

                    match self.index_batch(&batch).await {
                        Ok(_) => {}
                        Err(_) => {}
                    };

                    batch.clear();
                }
                Err(err) => {
                    println!("something went wrong {:?}", err);
                    return Ok(());
                }
            }
        }

        // if batch is emtpy we have nothing left to process
        if batch.is_empty() {
            return Ok(());
        }

        // otherwise process the rest
        match self.index_batch(&batch).await {
            Ok(_) => {}
            Err(err) => {
                println!("something went wrong while indexing batch {:?}", err);
            }
        };

        return Ok(());
    }

    async fn index_batch(self: &mut Self, batch: &Vec<BatchEntry>) -> Result<(), DirError> {
        println!("indexing batch");
        // extract content
        let content = batch.iter().map(|e| e.file_content.clone()).collect();

        // embed the content in the batch
        let embedding = self.embedder.embed(Input::Multiple(&content)).await.unwrap();

        // merge embeddings and file files
        let embedding_files = embedding
            .into_iter()
            .zip(content)
            .map(|(embedding_value, batch_entry)| EmbeddingFile {
                embedding: embedding_value.to_vec(),
                content: batch_entry,
            })
            .collect();

        // persist
        self.vector_store.store_batch(embedding_files).await;
        println!("done indexing batch");

        Ok(())
    }
}
