using System;
using System.Collections.Generic;
using Xunit.Abstractions;
using Xunit.Sdk;

namespace Tests.Common;

/// <summary>
/// pytest の `@pytest.mark.slow` に相当する xUnit の Trait 属性。
/// `dotnet test --filter "Category!=SlowOCR"` で除外できる。
/// </summary>
[TraitDiscoverer(
    "Tests.Common.SlowOcrAttribute+SlowOcrTraitDiscoverer",
    "OCRClipboard.Tests")]
[AttributeUsage(AttributeTargets.Method | AttributeTargets.Class, AllowMultiple = false)]
public sealed class SlowOcrAttribute : Attribute, ITraitAttribute
{
    private sealed class SlowOcrTraitDiscoverer : ITraitDiscoverer
    {
        public IEnumerable<KeyValuePair<string, string>> GetTraits(IAttributeInfo traitAttribute)
        {
            yield return new KeyValuePair<string, string>("Category", "SlowOCR");
        }
    }
}
