"use client";
import * as Tooltip from "@radix-ui/react-tooltip";
import { useEffect, useState } from "react";

export default function Home() {
  // サーバー数のstateを追加
  const [serverCount, setServerCount] = useState<string>("Loading...");

  useEffect(() => {
    // 強制的にダーククラスをルート(html)に付与して、常にダークモードで表示させる
    document.documentElement.classList.add("dark");
    // ブラウザの color-scheme も暗色に合わせる（フォーム系の色を暗くする目的）
    document.documentElement.style.colorScheme = "dark";
    return () => {
      document.documentElement.classList.remove("dark");
      document.documentElement.style.colorScheme = "";
    };
  }, []);

  // サーバー数取得
  useEffect(() => {
    fetch("/api/servers")
      .then((res) => res.json())
      .then((data) => {
        if (typeof data.guild_count === "number") {
          setServerCount(`${data.guild_count}`);
        }
      })
      .catch(() => {
        // 失敗時はデフォルト値のまま
      });
  }, []);

  const metrics = [
    { label: "SERVERS", value: serverCount },
    { label: "LATENCY", value: "~200ms" },
    { label: "DICTIONARY", value: "∞" },
  ];

  const features = [
    {
      title: "VOICEVOX Engine",
      tag: "自然な音声合成",
      desc: "VOICEVOXを採用し、自然で滑らかな音声を生成。",
      icon: "🔊",
    },
    {
      title: "Ultra Performance",
      tag: "専用GPU",
      desc: "GPUで高速生成。低遅延と高同時処理を両立。",
      icon: "⚡",
    },
    {
      title: "Intelligent Dictionary",
      tag: "無制限登録",
      desc: "高速DBで無制限（※2）に即時反映されるカスタム読み。",
      icon: "🧠",
    },
    {
      title: "HighSpeed Network",
      tag: "Ultra Low Latency",
      desc: "高速回線で200ms以下（※1）のレスポンスを目指す高速処理。",
      icon: "🌐",
    },
    {
      title: "Auto Return",
      tag: "自動復帰",
      desc: "再起動後も以前いたボイスチャンネルへ自動参加。",
      icon: "↩️",
    },
  ];

  const commands = [
    {
      cmd: "/join",
      title: "ボイスチャンネル参加",
      desc: "ワンコマンドで即座に開始",
    },
    {
      cmd: "/dictionary",
      title: "辞書機能",
      desc: "カスタム読み方登録",
    },
    {
      cmd: "/voice",
      title: "音声選択",
      desc: "パーソナライズ設定",
    },
    {
      cmd: "/leave",
      title: "切断",
      desc: "ボイスチャンネルから退出",
    },
    {
      cmd: "/speed",
      title: "スピード調整",
      desc: "話す速度を設定",
    },
  ];

  return (
    <Tooltip.Provider>
      <div className="dark relative min-h-screen flex flex-col overflow-hidden font-sans text-white">
        {/* 背景グラデ & 雲 */}
        <div className="absolute inset-0 bg-gradient-to-br from-sky-300 via-indigo-300 to-purple-300 dark:from-sky-900 dark:via-indigo-900 dark:to-purple-900" />
        <div className="pointer-events-none absolute inset-0">
          {[...Array(8)].map((_, i) => (
            <div
              key={i}
              className="cloud absolute rounded-full mix-blend-screen"
              style={{
                top: `${(i * 13) % 100}%`,
                left: `${(i * 23) % 100}%`,
                width: `${220 + (i % 3) * 180}px`,
                height: `${160 + (i % 4) * 140}px`,
                animationDelay: `${i * 2}s`,
                opacity: 0.25 + (i % 3) * 0.1,
              }}
            />
          ))}
        </div>

        <header className="relative z-10 w-full max-w-7xl mx-auto px-6 pt-10 flex flex-col gap-6">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center shadow-lg shadow-sky-900/20">
              <span className="text-xl">☁️</span>
            </div>
            <span className="tracking-wide font-medium text-white/80">
              Ultra Low Latency Voice bot
            </span>
          </div>
          <h1 className="text-4xl sm:text-6xl font-bold leading-[1.05]">
            <span className="bg-gradient-to-br from-white via-sky-100 to-white/70 dark:from-sky-200 dark:via-indigo-200 dark:to-purple-200 bg-clip-text text-transparent drop-shadow">
              Swiftly読み上げbot
            </span>
          </h1>
          <p className="max-w-2xl text-lg sm:text-xl text-white/80 leading-relaxed">
            VOICEVOXエンジンを使用した高速で無駄のない読み上げbot。
            低遅延で設定は必要ありません。
          </p>
          <div className="flex flex-wrap gap-4">
            <a
              href="#start"
              className="group relative inline-flex items-center gap-2 rounded-full px-8 py-4 text-base font-semibold bg-gradient-to-br from-sky-500 via-indigo-500 to-purple-600 hover:from-sky-400 hover:via-indigo-400 hover:to-purple-500 transition shadow-lg shadow-sky-900/30"
            >
              Discord に追加
              <span className="text-xl group-hover:translate-x-0.5 transition">
                →
              </span>
            </a>
            <a
              href="#why"
              className="inline-flex items-center gap-2 rounded-full px-7 py-4 text-base font-semibold bg-white/15 hover:bg-white/25 backdrop-blur-md border border-white/30 transition"
            >
              Why Swiftly
            </a>
          </div>
          <div className="flex gap-6 flex-wrap pt-4">
            {metrics.map((m) => (
              <Tooltip.Root key={m.label}>
                <Tooltip.Trigger asChild>
                  <div className="flex flex-col min-w-[120px] px-4 py-3 rounded-xl bg-white/10 backdrop-blur border border-white/20 shadow-lg hover:shadow-xl transition">
                    <span className="text-2xl font-bold tracking-tight">
                      {m.value}
                    </span>
                    <span className="text-[11px] tracking-wider text-white/70">
                      {m.label}
                    </span>
                  </div>
                </Tooltip.Trigger>
                <Tooltip.Portal>
                  <Tooltip.Content
                    side="top"
                    className="px-3 py-2 rounded-md bg-black/80 text-xs text-white shadow-lg z-50"
                  >
                    {m.label === "SERVERS"
                      ? "稼働中のサーバー数"
                      : m.label === "LATENCY"
                      ? "平均応答遅延"
                      : "登録可能な辞書数"}
                    <Tooltip.Arrow className="fill-black/80" />
                  </Tooltip.Content>
                </Tooltip.Portal>
              </Tooltip.Root>
            ))}
          </div>
        </header>

        {/* Features */}
        <section
          id="why"
          className="relative z-10 w-full max-w-7xl mx-auto px-6 mt-20"
        >
          <h2 className="text-3xl sm:text-4xl font-bold mb-6">
            Swiftlyの特徴
            {/* <span className="ml-2 bg-white/20 px-3 py-1 rounded-full text-base font-medium backdrop-blur">
            Why Swiftly
          </span> */}
          </h2>
          <p className="text-white/75 max-w-2xl mb-10">
            超低遅延アーキテクチャとGPU最適化により、発話までのレスポンスを体感的に短縮。
            柔軟な辞書システムと自動復帰で運用負荷を極小化します。
          </p>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((f) => (
              <div
                key={f.title}
                className="group relative rounded-2xl p-[1px] bg-gradient-to-br from-white/30 via-white/5 to-white/0 hover:from-sky-300/40 hover:via-indigo-200/10 hover:to-purple-300/10 transition shadow-lg hover:shadow-2xl"
              >
                <div className="h-full rounded-2xl p-5 flex flex-col gap-3 bg-slate-50/10 dark:bg-slate-900/20 backdrop-blur-md border border-white/20">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 flex items-center justify-center rounded-xl bg-white/15 text-xl">
                      {f.icon}
                    </div>
                    <div className="flex flex-col">
                      <span className="font-semibold">{f.title}</span>
                      <span className="text-xs text-white/60 tracking-wide">
                        {f.tag}
                      </span>
                    </div>
                  </div>
                  <div className="text-sm text-white/70 leading-relaxed">
                    {f.desc}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Command Interface */}
        <section
          id="commands"
          className="relative z-10 w-full max-w-7xl mx-auto px-6 mt-28"
        >
          <div className="flex flex-col lg:flex-row gap-10">
            <div className="flex-1">
              <h2 className="text-3xl sm:text-4xl font-bold mb-6">
                Command Interface
              </h2>
              <p className="text-white/75 max-w-xl mb-6">
                ゼロ設定で操作はシンプル。直感的なスラッシュコマンドで、導入直後から自然な読み上げを提供。
              </p>
              <div className="rounded-2xl border border-white/20 bg-white/10 backdrop-blur p-6 shadow-lg hover:shadow-2xl transition">
                <ul className="space-y-4">
                  {commands.map((c) => (
                    <Tooltip.Root key={c.cmd}>
                      <Tooltip.Trigger asChild>
                        <li className="flex flex-col sm:flex-row sm:items-center gap-2 cursor-pointer">
                          <code className="px-3 py-1 rounded-md bg-white/15 text-sky-50 font-mono text-sm">
                            {c.cmd}
                          </code>
                          <div className="flex-1">
                            <span className="font-medium">{c.title}</span>
                            <span className="block text-xs text-white/60">
                              {c.desc}
                            </span>
                          </div>
                        </li>
                      </Tooltip.Trigger>
                      <Tooltip.Portal>
                        <Tooltip.Content
                          side="top"
                          className="px-3 py-2 rounded-md bg-black/80 text-xs text-white shadow-lg z-50"
                        >
                          {c.title}
                          <Tooltip.Arrow className="fill-black/80" />
                        </Tooltip.Content>
                      </Tooltip.Portal>
                    </Tooltip.Root>
                  ))}
                </ul>
              </div>
            </div>
            <div className="flex-1 relative">
              <div className="absolute -top-8 -right-4 w-72 h-72 bg-gradient-to-br from-sky-400/30 to-purple-400/10 rounded-full blur-3xl pointer-events-none" />
              <div className="relative rounded-2xl h-full min-h-[340px] border border-white/20 bg-gradient-to-br from-white/15 to-white/5 backdrop-blur p-8 flex flex-col gap-6 shadow-lg hover:shadow-2xl transition">
                <div>
                  <h3 className="text-xl font-semibold">Swiftlyの思想</h3>
                </div>
                <div className="text-sm text-white/75">
                  Swiftlyは、低遅延と高可用性を最優先に設計された音声合成システムです。ユーザー体験を損なわないために、以下の原則を重視しています。
                  <ul className="list-disc pl-5 space-y-2 text-sm text-white/75">
                    <li>ユーザーにとって不要な機能は導入しない</li>
                    <li>不要なレスポンスメッセージは排除する</li>
                    <li>必要なメトリクスのみを可視化する</li>
                    <li>ユーザー自身がボットに貢献できるようにする（オープンソース化）</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Ready / CTA */}
        <section
          id="start"
          className="relative z-10 w-full max-w-7xl mx-auto px-6 mt-32 mb-28"
        >
          <div className="relative rounded-3xl p-[2px] bg-gradient-to-br from-sky-300/60 via-indigo-300/30 to-purple-300/10 dark:from-sky-500/40 dark:via-indigo-500/20 dark:to-purple-500/10">
            <div className="rounded-3xl bg-white/10 backdrop-blur-xl border border-white/30 p-10 flex flex-col lg:flex-row gap-12 shadow-2xl hover:shadow-3xl transition">
              <div className="flex-1">
                <div>
                  <h2 className="text-3xl sm:text-4xl font-bold mb-6">
                    Ready to Transform
                  </h2>
                </div>
                <div className="text-white/75 max-w-xl mb-8">
                  インストール後すぐ使用可能。サーバー管理権限のみで導入でき、bot自体は管理者権限不要。高速かつ
                  安定した読み上げをあなたのコミュニティへ。
                </div>
                <div className="flex flex-wrap gap-5">
                  <a
                    href="https://discord.com/oauth2/authorize?client_id=1371465579780767824"
                    className="inline-flex items-center gap-2 rounded-full px-8 py-4 bg-gradient-to-r from-sky-500 via-indigo-500 to-purple-600 font-semibold shadow-lg hover:shadow-xl transition"
                  >
                    Discordサーバーに追加する
                    <span className="text-lg">→</span>
                  </a>
                  <a
                    href="#commands"
                    className="inline-flex items-center gap-2 rounded-full px-7 py-4 bg-white/15 hover:bg-white/25 backdrop-blur border border-white/30 font-medium"
                  >
                    コマンド一覧
                  </a>
                </div>
              </div>
              <div className="w-full max-w-sm">
                <div className="rounded-2xl border border-white/25 bg-white/10 backdrop-blur p-6 flex flex-col gap-4 shadow-lg hover:shadow-2xl transition">
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-semibold">導入する</span>
                  </div>
                  <ul className="text-sm space-y-2 text-white/80">
                    <li>完全無料</li>
                    <li>セットアップ時間 0s（※3）</li>
                    <li>24/365 稼働目標（※4）</li>
                    <li>無制限辞書（※2）</li>
                    <li>超低遅延 ~200ms（※1）</li>
                  </ul>
                  <a
                    href="https://discord.com/oauth2/authorize?client_id=1371465579780767824"
                    className="mt-2 inline-flex justify-center rounded-xl px-5 py-3 bg-gradient-to-br from-sky-400 to-indigo-500 font-semibold hover:from-sky-300 hover:to-indigo-400 transition"
                  >
                    今すぐ追加
                  </a>
                  <div className="text-[10px] leading-relaxed text-white/50 pt-2">
                    インストールにはサーバー管理権限が必要です。bot自体は管理者権限を要求しません。
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="relative z-10 px-6 pb-16 w-full max-w-7xl mx-auto text-[11px] text-white/55 space-y-3">
          <div className="h-px bg-gradient-to-r from-transparent via-white/30 to-transparent mb-4" />
          <ul className="space-y-1 leading-relaxed">
            <li>
              ※1 状況によっては200msを超える場合があります。ネットワーク/負荷要因。
            </li>
            <li>
              ※2 辞書登録は無制限ですが、サーバーのストレージ容量に依存します。
            </li>
            <li>
              ※3 インストール後、ボイスチャンネルに参加するだけで利用開始できます。
            </li>
            <li>※4 24/365稼働は保証されません。</li>
          </ul>
          <div className="pt-4 flex flex-wrap items-center gap-4 text-white/60">
            <span className="font-semibold">Swiftly読み上げbot</span>
            <span className="text-white/30">|</span>
            <a
              href="#why"
              className="hover:text-white/90 transition underline-offset-4 hover:underline"
            >
              特徴
            </a>
            <a
              href="#commands"
              className="hover:text-white/90 transition underline-offset-4 hover:underline"
            >
              コマンド
            </a>
            <a
              href="#start"
              className="hover:text-white/90 transition underline-offset-4 hover:underline"
            >
              導入
            </a>
          </div>
        </footer>

        <style jsx global>{`
          .cloud {
            background: radial-gradient(
                circle at 30% 30%,
                rgba(255, 255, 255, 0.8),
                rgba(255, 255, 255, 0)
              ),
              radial-gradient(
                circle at 70% 60%,
                rgba(255, 255, 255, 0.6),
                rgba(255, 255, 255, 0)
              );
            filter: blur(30px);
            animation: floatCloud 28s linear infinite;
          }
          @keyframes floatCloud {
            0% {
              transform: translate3d(-5%, 0, 0) scale(1);
            }
            50% {
              transform: translate3d(8%, -4%, 0) scale(1.08);
            }
            100% {
              transform: translate3d(-5%, 0, 0) scale(1);
            }
          }
        `}</style>
      </div>
    </Tooltip.Provider>
  );
}
