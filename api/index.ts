import * as dotenv from "dotenv";
import { Pinecone } from "@pinecone-database/pinecone";
import OpenAi from "openai";
dotenv.config();
const API: string = process.env.PINECONE_API_KEY || "";
const openai = new OpenAi({
  apiKey: process.env.OPENAI_API_KEY || "",
  baseURL: "https://models.inference.ai.azure.com",
});
const pc = new Pinecone({
  apiKey: API,
});
const index = pc.index("rag-index");

const getEmbedding = async (text: string): Promise<number[]> => {
  const response = await openai.embeddings.create({
    model: "text-embedding-3-large",
    input: text,
  });

  return response.data[0].embedding;
};

const storeChunks = async (
  chunks: Array<{ text: string; url: string; title: string }>
) => {
  let vectors: any = [];
  for (let i = 0; i < chunks.length; i++) {
    const chunk = chunks[i];
    const embedding = await getEmbedding(chunk.text);

    vectors.push({
      id: `${chunk.url.replace(/[^a-zA-Z0-9]/g, "_")}_chunk_${i}`,
      values: embedding,
      metadata: {
        text: chunk.text,
        url: chunk.url,
        title: chunk.title,
        chunk_index: i,
        timestamp: new Date().toISOString(),
      },
    });
  }

  await index.upsert(vectors);
};

const queryRelevantChunks = async (query: string, topK = 5) => {
  const queryEmbedding = await getEmbedding(query);

  const result = await index.query({
    vector: queryEmbedding,
    topK,
    includeMetadata: true,
  });

  return result.matches.map((match) => {
    text: match.metadata?.text;
    url: match.metadata?.url;
    score: match.score;
  });
};

// VectorData {
//   id: string;
//   values: number[];
//   metadata: {
//     text: string;
//     url: string;
//     title?: string;
//     chunk_index: number;
//     timestamp: string;
//     content_type?: string;
//   }
// }
