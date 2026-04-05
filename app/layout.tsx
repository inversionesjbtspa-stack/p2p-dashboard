export const metadata = {
  title: "Inversiones JBT Dashboard",
  description: "Dashboard P2P CLP/USDT"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body style={{ margin: 0, fontFamily: "Arial", background: "#F7F7F5" }}>
        {children}
      </body>
    </html>
  );
}
