import OpenAI from 'openai';
import { bedrock } from 'openai/providers/bedrock';
const mode = process.argv[2];
if (mode === '--check') {
  console.log('READY openai-node Bedrock provider; no AWS request');
} else if (mode === '--live') {
  const key = process.env.AWS_BEARER_TOKEN_BEDROCK;
  if (!key) throw new Error('AWS_BEARER_TOKEN_BEDROCK is required for --live');
  const client = new OpenAI({ provider: bedrock({ region: 'us-east-1', apiKey: key }) });
  const response = await client.responses.create({
    model: 'openai.gpt-6-sol',
    input: 'Reply with one sentence describing an offline development check.',
  });
  console.log(response.output_text);
} else {
  throw new Error('Pass --check or --live');
}
