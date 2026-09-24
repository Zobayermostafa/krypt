import Icon from './Icon'

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
      className="download-button"
    >
      <Icon name="download" size={16} />
      <span>{label}</span>
    </a>
  )
}
