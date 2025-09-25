import HomeClient from "./HomeClient";

export const metadata = {
  title: "Swiftly読み上げbot | Discord Bot - 低遅延・高品質TTS",
  description:
    "【公式】Swiftly読み上げbotは、Discordサーバー向けの超高速・低遅延・高品質な日本語テキスト読み上げ（TTS）ボットです。無料で簡単導入、VOICEVOX対応、24時間稼働、カスタマイズ可能。初心者にもおすすめの最強Discord読み上げbot。導入方法・使い方・サポートも充実。",
};

export default function Home() {
  return <HomeClient />;
}