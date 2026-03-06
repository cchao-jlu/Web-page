import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const MODEL_PRESETS = [
  { label: "Auto (let provider decide)", value: "" },
  { label: "Qwen/Qwen2.5-7B-Instruct", value: "Qwen/Qwen2.5-7B-Instruct" },
  { label: "Meta-Llama-3.1-8B-Instruct", value: "meta-llama/Meta-Llama-3.1-8B-Instruct" },
  { label: "Mistral-7B-Instruct", value: "mistralai/Mistral-7B-Instruct-v0.3" }
];

export default function App() {
  const [topic, setTopic] = useState("大模型发展");
  const [lang, setLang] = useState("zh");
  const [minSources, setMinSources] = useState(3);
  const [maxResults, setMaxResults] = useState(8);
  const [maxPages, setMaxPages] = useState(5);
  const [provider, setProvider] = useState("auto");
  const [modelId, setModelId] = useState("");
  const [customModel, setCustomModel] = useState("");
  const [allowDomains, setAllowDomains] = useState("");
  const [blockDomains, setBlockDomains] = useState("");
  const [token, setToken] = useState("");
  const [reportId, setReportId] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!reportId) return;
    let active = true;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/reports/${reportId}`);
        const data = await res.json();
        if (!active) return;
        setReport(data);
        if (data.status !== "running") {
          clearInterval(interval);
          setLoading(false);
        }
      } catch (err) {
        if (!active) return;
        setError("无法获取报告状态");
        setLoading(false);
        clearInterval(interval);
      }
    }, 2500);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [reportId]);

  const startRun = async () => {
    setError(null);
    setReport(null);
    setLoading(true);

    const payload = {
      topic,
      lang,
      min_sources: Number(minSources),
      max_results: Number(maxResults),
      max_pages: Number(maxPages),
      provider: provider && provider !== "auto" ? provider : null,
      model_id: modelId || customModel || null,
      allow_domains: allowDomains
        ? allowDomains.split(",").map((s) => s.trim()).filter(Boolean)
        : null,
      block_domains: blockDomains
        ? blockDomains.split(",").map((s) => s.trim()).filter(Boolean)
        : null,
      token: token || null
    };

    try {
      const res = await fetch(`${API_BASE}/api/reports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "请求失败");
      }
      const data = await res.json();
      setReportId(data.id);
    } catch (err) {
      setError(err.message || "请求失败");
      setLoading(false);
    }
  };

  const displayModel = modelId === "__custom__" ? customModel : modelId;
  const stages = report?.stages || {};

  return (
    <div className="min-h-screen px-6 py-10">
      <div className="mx-auto max-w-5xl space-y-6">
        <header className="space-y-2">
          <p className="text-sm uppercase tracking-[0.3em] text-sage">Web Info Collector</p>
          <h1 className="font-display text-3xl sm:text-4xl">多阶段研究管线</h1>
          <p className="text-base text-neutral-600">
            检索 → 证据压缩 → 结构化大纲 → 报告合成。可配置多模型与来源过滤。
          </p>
        </header>

        <section className="card space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-semibold">主题</label>
              <input
                className="w-full rounded-xl border border-sand bg-white px-3 py-2"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-semibold">输出语言</label>
              <select
                className="w-full rounded-xl border border-sand bg-white px-3 py-2"
                value={lang}
                onChange={(e) => setLang(e.target.value)}
              >
                <option value="zh">中文</option>
                <option value="en">English</option>
              </select>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <label className="text-sm font-semibold">最少来源数</label>
              <input
                className="w-full rounded-xl border border-sand bg-white px-3 py-2"
                type="number"
                min="1"
                value={minSources}
                onChange={(e) => setMinSources(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-semibold">搜索结果数量</label>
              <input
                className="w-full rounded-xl border border-sand bg-white px-3 py-2"
                type="number"
                min="3"
                value={maxResults}
                onChange={(e) => setMaxResults(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-semibold">抓取页面数量</label>
              <input
                className="w-full rounded-xl border border-sand bg-white px-3 py-2"
                type="number"
                min="1"
                value={maxPages}
                onChange={(e) => setMaxPages(e.target.value)}
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-semibold">Provider</label>
              <input
                className="w-full rounded-xl border border-sand bg-white px-3 py-2"
                placeholder="auto / hf-inference / openai"
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-semibold">HF Token (可选)</label>
              <input
                className="w-full rounded-xl border border-sand bg-white px-3 py-2"
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-semibold">模型预设</label>
              <select
                className="w-full rounded-xl border border-sand bg-white px-3 py-2"
                value={modelId}
                onChange={(e) => setModelId(e.target.value)}
              >
                {MODEL_PRESETS.map((item) => (
                  <option key={item.label} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-semibold">自定义模型 ID</label>
              <input
                className="w-full rounded-xl border border-sand bg-white px-3 py-2"
                placeholder="仅当需要覆盖预设时填写"
                value={customModel}
                onChange={(e) => setCustomModel(e.target.value)}
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-semibold">允许域名 (逗号分隔)</label>
              <input
                className="w-full rounded-xl border border-sand bg-white px-3 py-2"
                placeholder="gov.cn, who.int"
                value={allowDomains}
                onChange={(e) => setAllowDomains(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-semibold">屏蔽域名 (逗号分隔)</label>
              <input
                className="w-full rounded-xl border border-sand bg-white px-3 py-2"
                placeholder="weibo.com, zhihu.com"
                value={blockDomains}
                onChange={(e) => setBlockDomains(e.target.value)}
              />
            </div>
          </div>

          <button
            className="mt-2 w-full rounded-full bg-clay px-5 py-3 font-semibold text-white shadow-soft transition hover:translate-y-[-1px]"
            onClick={startRun}
            disabled={loading}
          >
            {loading ? "生成中..." : "开始生成"}
          </button>

          {error && <p className="text-red-700">{error}</p>}
        </section>

        <section className="card space-y-3">
          <h2 className="font-display text-2xl">阶段进度</h2>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-xl border border-sand bg-white p-4 text-sm">
              <p className="font-semibold">1. 检索</p>
              <p className="text-neutral-500">{stages.retrieval ? `来源数: ${stages.retrieval.sources}` : "等待中"}</p>
            </div>
            <div className="rounded-xl border border-sand bg-white p-4 text-sm">
              <p className="font-semibold">2. 证据压缩</p>
              <p className="text-neutral-500">{stages.compression ? `压缩条目: ${stages.compression.items}` : "等待中"}</p>
            </div>
            <div className="rounded-xl border border-sand bg-white p-4 text-sm">
              <p className="font-semibold">3. 结构化大纲</p>
              <p className="text-neutral-500">{stages.outline ? "已生成" : "等待中"}</p>
            </div>
            <div className="rounded-xl border border-sand bg-white p-4 text-sm">
              <p className="font-semibold">4. 报告合成</p>
              <p className="text-neutral-500">{stages.report ? `长度: ${stages.report.length}` : "等待中"}</p>
            </div>
          </div>
        </section>

        <section className="card space-y-3">
          <h2 className="font-display text-2xl">运行状态</h2>
          {report ? (
            <div className="space-y-3 text-sm text-neutral-700">
              <p>
                <span className="font-semibold">状态:</span> {report.status}
              </p>
              <p>
                <span className="font-semibold">模型:</span> {displayModel || "auto"}
              </p>
              {report.error && <p className="text-red-700">错误: {report.error}</p>}
              {report.summary_md && (
                <pre className="whitespace-pre-wrap rounded-xl border border-sand bg-white p-4 text-xs">
                  {report.summary_md}
                </pre>
              )}
            </div>
          ) : (
            <p className="text-sm text-neutral-500">提交后会显示生成进度。</p>
          )}
        </section>
      </div>
    </div>
  );
}
