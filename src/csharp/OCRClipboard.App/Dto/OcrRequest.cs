using System.Text.Json.Serialization;

namespace OCRClipboard.App.Dto;

public sealed class OcrRequest
{
    [JsonPropertyName("language")] public string Language { get; set; } = "eng";
    // source: "clipboard" or "imageBase64"
    [JsonPropertyName("source")] public string Source { get; set; } = "clipboard";
    // when source == "imageBase64"
    [JsonPropertyName("imageBase64")] public string? ImageBase64 { get; set; }
}

public sealed class OcrResponse
{
    [JsonPropertyName("text")] public string Text { get; set; } = string.Empty;
    [JsonPropertyName("confidence")] public double Confidence { get; set; }
}
