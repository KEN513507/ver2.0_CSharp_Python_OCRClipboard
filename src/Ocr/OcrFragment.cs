using System.Drawing;

namespace Ocr;

public sealed record OcrFragment(string Text, double Confidence, Rectangle Bounds);
