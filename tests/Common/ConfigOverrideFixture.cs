using System;
using System.Collections.Generic;

namespace Tests.Common;

/// <summary>
/// 環境変数で QualityConfig を一時的に書き換えるフィクスチャ。
/// pytest の monkeypatch.setenv 相当。
/// </summary>
public sealed class ConfigOverrideFixture : IDisposable
{
    private readonly Dictionary<string, string?> _originals = new();

    public ConfigOverrideFixture WithEnv(string name, string value)
    {
        if (!_originals.ContainsKey(name))
            _originals[name] = Environment.GetEnvironmentVariable(name);
        Environment.SetEnvironmentVariable(name, value);
        return this;
    }

    public void Dispose()
    {
        foreach (var (key, value) in _originals)
            Environment.SetEnvironmentVariable(key, value);
    }
}
