using System;
using Xunit;
using Xunit.Sdk;

namespace Tests.Common;

/// <summary>
/// pytest の `@pytest.mark.slow` に相当する xUnit の Trait 属性。
/// </summary>
[AttributeUsage(AttributeTargets.Method | AttributeTargets.Class)]
public sealed class SlowOcrAttribute : TraitAttribute
{
    public SlowOcrAttribute() : base("Category", "SlowOCR") { }
}
