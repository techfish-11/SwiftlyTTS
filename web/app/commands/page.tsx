import Link from "next/link";
export const metadata = {
  title: "コマンド一覧 | Swiftly読み上げbot",
  description: "Swiftly読み上げbotで利用できるコマンドの一覧です。",
};
const commands = [
  {
    cmd: "/join",
    title: "ボイスチャンネル参加",
    usage: "/join",
    desc: "Botを自分が参加しているボイスチャンネルに呼びます。最初にこのコマンドを実行してください。",
    example: "/join",
  },
  {
    cmd: "/dictionary",
    title: "辞書機能",
    usage: "/dictionary 単語 よみかた",
    desc: "指定した単語の読み方をカスタマイズできます。サーバーごとに登録可能です。",
    example: "/dictionary 甲斐田 かいだ",
  },
  {
    cmd: "/dictionary-list",
    title: "辞書一覧",
    usage: "/dictionary-list",
    desc: "サーバーに登録されている辞書の一覧を表示します。",
    example: "/dictionary-list",
  },
  {
    cmd: "/dictionary-remove",
    title: "辞書削除",
    usage: "/dictionary-remove 単語",
    desc: "指定した単語の読み方を削除します。サーバーごとに登録された辞書から削除されます。",
    example: "/dictionary-remove 甲斐田",
  },
  {
    cmd: "/dictionary-search",
    title: "辞書検索",
    usage: "/dictionary-search 単語",
    desc: "指定した単語の読み方を検索します。サーバーごとに登録された辞書から検索されます。",
    example: "/dictionary-search 甲斐田",
  },
  {
    cmd: "/voice",
    title: "音声選択",
    usage: "/voice",
    desc: "自分の読み上げ音声を選択できます。コマンド実行後、番号を入力して話者を設定します。",
    example: "/voice",
  },
  {
    cmd: "/leave",
    title: "切断",
    usage: "/leave",
    desc: "Botをボイスチャンネルから退出させます。",
    example: "/leave",
  },
  {
    cmd: "/speed",
    title: "スピード調整",
    usage: "/speed [数値 or 空白]",
    desc: "サーバー全体の読み上げ速度を設定します。1.0～2.0の間で指定できます。resetでデフォルトに戻します。",
    example: "/speed 1.2",
  },

  {
    cmd: "/admin",
    title: "管理者コマンド（bot管理者専用）",
    usage: "/admin [コマンド]",
    desc: "管理者専用のコマンドを実行します。",
  },
  {
    cmd: "s",
    title: "読み上げキュー削除 & 読み上げ停止",
    usage: "s",
    desc: "sと読み上げチャンネルに送信すると、現在の読み上げキューを削除し、現在読み上げているメッセージの読み上げを停止します。スパムされた場合などに有効です。",
  },
];

export default function CommandsPage() {
  return (
    <div className="dark min-h-screen bg-gradient-to-br from-sky-900 via-indigo-900 to-purple-900 text-white font-sans px-6 py-12">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-4xl font-bold mb-8">コマンド使用方法</h1>
        <p className="mb-10 text-white/80">
          Swiftly読み上げbotで利用できる主なコマンドとその使い方をまとめました。
        </p>
        <div className="space-y-8">
          {commands.map((c) => (
            <div
              key={c.cmd}
              className="rounded-xl bg-white/10 border border-white/20 p-6 shadow-lg"
            >
              <div className="flex items-center gap-3 mb-2">
                <code className="px-3 py-1 rounded-md bg-white/15 text-sky-50 font-mono text-base">
                  {c.cmd}
                </code>
                <span className="font-semibold text-lg">{c.title}</span>
              </div>
              <div className="mb-2 text-white/80">{c.desc}</div>
              <div className="mb-1">
                <span className="text-white/60 text-sm">使い方：</span>
                <span className="ml-2 font-mono bg-white/15 px-2 py-1 rounded">{c.usage}</span>
              </div>
              <div>
                <span className="text-white/60 text-sm">例：</span>
                <span className="ml-2 font-mono bg-white/10 px-2 py-1 rounded">{c.example}</span>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-12">
          <Link
            href="/"
            className="inline-block mt-4 px-6 py-3 rounded-full bg-gradient-to-br from-sky-500 via-indigo-500 to-purple-600 font-semibold shadow hover:from-sky-400 hover:to-purple-500 transition"
          >
            ← トップページへ戻る
          </Link>
        </div>
      </div>
    </div>
  );
}
