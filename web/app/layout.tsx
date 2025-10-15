import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Script from "next/script";
import NextAuthProvider from "./providers/SessionProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "Swiftly読み上げbot | Discord Bot - 低遅延・高品質TTS",
    template: "%s | swiftlybot.com",
  },
  description:
    "【公式】Swiftly読み上げbotは、Discordサーバー向けの超高速・低遅延・高品質な日本語テキスト読み上げ（TTS）ボットです。無料で簡単導入、VOICEVOX対応、24時間稼働、カスタマイズ可能。初心者にもおすすめの最強Discord読み上げbot。導入方法・使い方・サポートも充実。",
  keywords: [
    "Swiftly読み上げbot",
    "Discord ボット",
    "テキスト読み上げ",
    "TTS",
    "音声合成",
    "低遅延",
    "日本語TTS",
    "Discord Voice",
    "導入方法",
    "セットアップ",
    "読み上げボット",
    "Discord読み上げbot",
    "Discord読み上げbotおすすめ",
    "Discord bot",
    "無料",
    "読み上げbot",
    "VOICEVOX",
    "高品質TTS",
    "24時間稼働",
    "カスタマイズ",
    "初心者向け",
    "公式",
    "使い方",
    "サポート",
    "Swiftly",
    "swiftlybot.com"
  ],
  metadataBase: new URL("https://swiftlybot.com"),
  authors: [
    { name: "techfish", url: "https://techfish.dev" },
    { name: "11sakana", url: "https://x.com/11sakana1" }
  ],
  creator: "techfish",
  publisher: "Swiftly",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0f172a" }
  ],
  alternates: {
    canonical: "https://swiftlybot.com/"
  },
  icons: {
    icon: "https://cdn.sakana11.org/swiftly/favicon.ico",
    apple: "https://cdn.sakana11.org/swiftly/apple-touch-icon.png",
    shortcut: "https://cdn.sakana11.org/swiftly/favicon-16x16.png"
  },
  openGraph: {
    title: "Swiftly読み上げbot | 低遅延・高品質TTS for Discord",
    description:
      "Swiftly読み上げbotは、Discord向けの超高速・低遅延・高品質な日本語テキスト読み上げ（TTS）ボット。無料・簡単導入・VOICEVOX対応・24時間稼働・初心者にもおすすめ。最強のDiscord読み上げbotを今すぐ導入！",
    url: "https://swiftlybot.com/",
    siteName: "Swiftly読み上げbot",
    images: [
      {
        url: "/banner.png",
        width: 1200,
        height: 630,
        alt: "Swiftly読み上げbot - Ultra Low Latency Voice Synthesis",
      },
      {
        url: "/banner.png",
        width: 1200,
        height: 630,
        alt: "Swiftly - Discord TTS preview",
      }
    ],
    type: "website",
    locale: "ja_JP"
  },
  twitter: {
    card: "summary_large_image",
    title: "Swiftly読み上げbot | Discord最強の低遅延TTSボット",
    description:
      "Swiftly読み上げbotは、Discord向けの超高速・低遅延・高品質な日本語TTSボット。無料・VOICEVOX対応・24時間稼働・初心者にもおすすめ。今すぐ導入！",
    images: ["/banner.png"],
    creator: "@11sakana1",
    site: "@11sakana1"
  },
  robots: {
    index: true,
    follow: true,
    nocache: false,
    "googleBot": {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1
    }
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {/* Google Analytics */}
        <Script
          src="https://www.googletagmanager.com/gtag/js?id=G-Y8PXX5VS86"
          strategy="afterInteractive"
        />
        <Script id="google-analytics" strategy="afterInteractive">
          {`window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', 'G-87Y83Q8YVW');`}
        </Script>

        <NextAuthProvider>
          {children}
        </NextAuthProvider>
      </body>
    </html>
  );
}
