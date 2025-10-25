using System.Text.Json.Serialization;

namespace OCRClipboard.App.Dto;

public sealed class ErrorResponse
{
    [JsonPropertyName("code")] public string Code { get; set; } = "error";
    [JsonPropertyName("message")] public string Message { get; set; } = string.Empty;
}

