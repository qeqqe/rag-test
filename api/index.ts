import * as dotenv from "dotenv";
import { Pinecone } from "@pinecone-database/pinecone";
import OpenAi from "openai";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";

const execAsync = promisify(exec);

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

const scrapeAndChunk = async (
  url: string
): Promise<Array<{ text: string; url: string; title: string }>> => {
  try {
    const scriptPath = path.join(
      __dirname,
      "..",
      "helper",
      "sequential-scraping.py"
    );
    const command = `uv run ${scriptPath} --url ${url}`;

    const { stdout, stderr } = await execAsync(command);

    if (stderr) {
      console.error("Python script stderr:", stderr);
    }

    const chunks = JSON.parse(stdout);
    return chunks;
  } catch (error) {
    console.error("Error running Python scraper:", error);
    throw new Error(`Failed to scrape and chunk URL: ${url}`);
  }
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

const scrapeAndStore = async (url: string) => {
  try {
    console.log(`Starting scrape and store for: ${url}`);

    const chunks = await scrapeAndChunk(url);
    console.log(`Scraped ${chunks.length} chunks from ${url}`);

    await storeChunks(chunks);
    console.log(
      `Successfully stored ${chunks.length} chunks in vector database`
    );

    return {
      success: true,
      chunksProcessed: chunks.length,
      url: url,
    };
  } catch (error) {
    console.error(`Error in scrapeAndStore:`, error);
    throw error;
  }
};

const queryRelevantChunks = async (query: string, topK = 5) => {
  const queryEmbedding = await getEmbedding(query);

  const result = await index.query({
    vector: queryEmbedding,
    topK,
    includeMetadata: true,
  });

  return result.matches.map((match) => ({
    text: match.metadata?.text,
    url: match.metadata?.url,
    score: match.score,
  }));
};

// Export functions for use
export {
  scrapeAndChunk,
  storeChunks,
  scrapeAndStore,
  queryRelevantChunks,
  getEmbedding,
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
