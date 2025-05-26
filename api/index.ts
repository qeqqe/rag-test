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
