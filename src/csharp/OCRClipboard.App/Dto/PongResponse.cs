using System.Text.Json.Serialization;

namespace OCRClipboard.App.Dto;

public sealed class PongResponse
{
    [JsonPropertyName("ok")] public bool Ok { get; set; }
    [JsonPropertyName("ts")] public long? Timestamp { get; set; }
    [JsonPropertyName("pid")] public int Pid { get; set; }
    [JsonPropertyName("ver")] public string? Version { get; set; }
    [JsonPropertyName("error")] public string? Error { get; set; }
    [JsonPropertyName("warmed")] public string[]? WarmedLangs { get; set; }
}
