// Setup type definitions for built-in Supabase Runtime APIs
import "jsr:@supabase/functions-js/edge-runtime.d.ts";

// We'll use the OpenAI API to generate embeddings
import OpenAI from "jsr:@openai/openai";

// Initialize OpenAI client
const openai = new OpenAI({
  // We'll need to manually set the `OPENAI_API_KEY` environment variable
  apiKey: Deno.env.get("OPENAI_API_KEY"),
});

Deno.serve(async (req) => {
  // This is an example of a POST request handler.
  const { query } = await req.json();

  // Generate embedding for the query.
  const embedding = await generateEmbedding(query);

  return new Response(JSON.stringify({ embedding }), {
    headers: { "Content-Type": "application/json" },
  });
});

/**
 * Generates an embedding for the given text.
 */
async function generateEmbedding(text: string) {
  const response = await openai.embeddings.create({
    model: "text-embedding-3-small",
    dimensions: 384, // Match database vector(384)
    input: text,
  });
  const [data] = response.data;

  if (!data) {
    throw new Error("failed to generate embedding");
  }

  return data.embedding;
}
