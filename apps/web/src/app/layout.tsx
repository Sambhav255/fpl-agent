import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "Touchline | FPL Assistant", description: "Local, explainable Fantasy Premier League planning" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
