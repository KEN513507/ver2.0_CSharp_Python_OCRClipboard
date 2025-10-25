using System.Text.Json;
using System.Text.Json.Serialization;

namespace OCRClipboard.App.Dto;

public sealed class Envelope
{
    [JsonPropertyName("id")] public string Id { get; set; } = Guid.NewGuid().ToString();
    [JsonPropertyName("type")] public string Type { get; set; } = string.Empty;
    [JsonPropertyName("payload")] public JsonElement Payload { get; set; }
}

