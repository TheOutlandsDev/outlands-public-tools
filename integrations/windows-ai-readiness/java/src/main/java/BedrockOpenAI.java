import com.openai.client.OpenAIClient;
import com.openai.client.okhttp.BedrockOpenAIOkHttpClient;
import com.openai.models.responses.ResponseCreateParams;

public final class BedrockOpenAI {
    private BedrockOpenAI() {}

    public static void main(String[] args) {
        if (args.length != 1) {
            throw new IllegalArgumentException("Pass --check or --live");
        }
        if ("--check".equals(args[0])) {
            System.out.println("READY java " + Runtime.version() + "; no AWS request");
            return;
        }
        if (!"--live".equals(args[0])) {
            throw new IllegalArgumentException("Pass --check or --live");
        }
        String key = System.getenv("AWS_BEARER_TOKEN_BEDROCK");
        if (key == null || key.isBlank()) {
            throw new IllegalStateException("AWS_BEARER_TOKEN_BEDROCK is required for --live");
        }
        OpenAIClient client = BedrockOpenAIOkHttpClient.builder()
                .awsRegion("us-east-1")
                .apiKey(key)
                .build();
        ResponseCreateParams params = ResponseCreateParams.builder()
                .model("openai.gpt-6-sol")
                .input("Reply with one sentence describing an offline development check.")
                .build();
        client.responses().create(params).output().stream()
                .flatMap(item -> item.message().stream())
                .flatMap(message -> message.content().stream())
                .flatMap(content -> content.outputText().stream())
                .forEach(text -> System.out.println(text.text()));
    }
}
