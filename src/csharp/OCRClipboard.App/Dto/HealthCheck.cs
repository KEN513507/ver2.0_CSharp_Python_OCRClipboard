using System.Text.Json.Serialization;

namespace OCRClipboard.App.Dto;

public sealed class HealthCheck
{
    [JsonPropertyName("reason")] public string? Reason { get; set; }
}

public sealed class HealthOk
{
    [JsonPropertyName("message")] public string Message { get; set; } = "ok";
}

