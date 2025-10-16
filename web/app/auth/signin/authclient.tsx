"use client";
import { signIn } from "next-auth/react";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Avatar from "@mui/material/Avatar";
import Stack from "@mui/material/Stack";
import { blueGrey } from "@mui/material/colors";
import { FaDiscord } from "react-icons/fa";

export default function SignInPage() {
  return (
    <Box sx={{ minHeight: "100vh", bgcolor: blueGrey[50], display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Paper elevation={8} sx={{ p: 5, borderRadius: 4, minWidth: 340, maxWidth: 400, mx: 2 }}>
        <Stack spacing={3} alignItems="center">
          <Avatar sx={{ bgcolor: "#5865F2", width: 64, height: 64 }}>
            <FaDiscord size={38} />
          </Avatar>
          <Typography variant="h5" fontWeight={700} color="text.primary">
            Discordログイン
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center">
            SwiftlyTTSのWeb機能を利用するには、Discordアカウントでログインしてください。
          </Typography>
          <Button
            variant="contained"
            size="large"
            startIcon={<FaDiscord size={24} />}
            sx={{
              bgcolor: "#5865F2",
              color: "#fff",
              fontWeight: 700,
              borderRadius: 2,
              textTransform: "none",
              fontSize: 18,
              px: 4,
              py: 1.5,
              boxShadow: 2,
              '&:hover': { bgcolor: "#4752C4" },
              mt: 2,
            }}
            onClick={() => signIn("discord", { callbackUrl: `${window.location.origin}/dashboard` })}
          >
            Discordでログイン
          </Button>
        </Stack>
      </Paper>
    </Box>
  );
}
