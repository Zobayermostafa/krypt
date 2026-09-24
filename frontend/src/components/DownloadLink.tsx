interface DownloadLinkProps {
  url: string
  filename: string
  label: string
  icon?: string
}

export default function DownloadLink({ url, filename, label, icon = '⬇️' }: DownloadLinkProps) {
  return (
    <a
      href={url}
      download={filename}
      className="
        inline-flex items-center justify-center gap-2 px-4 py-2.5
        bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white text-sm font-semibold
        rounded-xl shadow transition-all duration-150
      "
    >
      <span>{icon}</span>
      <span>{label}</span>
    </a>
  )
}
