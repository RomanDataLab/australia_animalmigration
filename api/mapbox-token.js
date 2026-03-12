export default function handler(req, res) {
  const token = process.env.MAPBOX_PUBLIC_TOKEN || "";
  const style = process.env.MAPBOX_STYLE || "mapbox://styles/mapbox/dark-v10";

  res.setHeader("Cache-Control", "no-store");
  res.status(200).json({ token, style });
}
