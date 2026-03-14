use crate::offline::vault::{OfflineVault, VaultError};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocalSearchResult {
    pub chunk_id: String,
    pub content: String,
    pub source_title: String,
    pub score: f32,
}

pub struct LocalSearch;

impl LocalSearch {
    /// Search locally cached embeddings using cosine similarity.
    /// Returns top_k results sorted by score descending.
    pub fn search(
        vault: &OfflineVault,
        owner_id: &str,
        query_embedding: &[f32],
        top_k: usize,
    ) -> Result<Vec<LocalSearchResult>, VaultError> {
        let all = vault.get_all_embeddings(owner_id)?;

        let mut scored: Vec<LocalSearchResult> = all
            .iter()
            .map(|e| {
                let score = cosine_similarity(query_embedding, &e.embedding);
                LocalSearchResult {
                    chunk_id: e.chunk_id.clone(),
                    content: e.content.clone(),
                    source_title: e.source_title.clone(),
                    score,
                }
            })
            .collect();

        scored.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
        scored.truncate(top_k);

        Ok(scored)
    }
}

fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() || a.is_empty() {
        return 0.0;
    }

    let mut dot = 0.0f32;
    let mut norm_a = 0.0f32;
    let mut norm_b = 0.0f32;

    for (x, y) in a.iter().zip(b.iter()) {
        dot += x * y;
        norm_a += x * x;
        norm_b += y * y;
    }

    let denom = norm_a.sqrt() * norm_b.sqrt();
    if denom == 0.0 {
        0.0
    } else {
        dot / denom
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cosine_identical() {
        let v = vec![1.0, 2.0, 3.0];
        let sim = cosine_similarity(&v, &v);
        assert!((sim - 1.0).abs() < 1e-6);
    }

    #[test]
    fn test_cosine_orthogonal() {
        let a = vec![1.0, 0.0];
        let b = vec![0.0, 1.0];
        let sim = cosine_similarity(&a, &b);
        assert!(sim.abs() < 1e-6);
    }

    #[test]
    fn test_cosine_empty() {
        let sim = cosine_similarity(&[], &[]);
        assert_eq!(sim, 0.0);
    }
}
