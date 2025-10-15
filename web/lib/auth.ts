import DiscordProvider from "next-auth/providers/discord";

export const authOptions = {
  providers: [
    DiscordProvider({
      clientId: process.env.DISCORD_CLIENT_ID!,
      clientSecret: process.env.DISCORD_CLIENT_SECRET!,
      // request guilds scope so we can read user's guilds
      authorization: { params: { scope: "identify guilds" } },
    }),
  ],
  secret: process.env.NEXTAUTH_SECRET,
  callbacks: {
    // After sign in, redirect to the dashboard
    async redirect({ url, baseUrl }: { url: string; baseUrl: string }) {
      // If a callbackUrl was provided and it's on our site, use it. Otherwise fallback to dashboard.
      try {
        if (typeof url === "string" && url.startsWith(baseUrl)) return url;
      } catch {
        // ignore and fallback
      }
      return `${baseUrl}/dashboard`;
    },
    // Persist the access token to the token object so we can use it server-side
    async jwt({
      token,
      account,
    }: {
      token: import("next-auth/jwt").JWT;
      account?: import("next-auth").Account | null;
    }) {
      if (account) {
        token.accessToken = account.access_token;
      }
      return token;
    },
    // Make the access token and user id available in the session object on the client
    async session({
      session,
      token,
    }: {
      session: import("next-auth").Session;
      token: import("next-auth/jwt").JWT;
    }) {
      if (typeof token.accessToken === "string") {
        session.accessToken = token.accessToken;
      }
      if (session.user && token.sub) {
        session.user.id = token.sub;
      }
      return session;
    },
  },
};

export default authOptions;
