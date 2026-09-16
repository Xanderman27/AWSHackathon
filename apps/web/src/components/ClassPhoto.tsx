// Classroom photos are authorised per request, so they cannot be dropped into an <img src>:
// the role headers this app authenticates with do not ride along on an image request.
// We fetch the bytes through the normal API client and hand the <img> an object URL.
//
// In production these become short-lived presigned S3 URLs (TECH_STACK, "Delivery and
// config"); the authorisation check on the server is the part that stays.

import { useEffect, useState } from 'react'
import { apiBlob } from '../api'

export default function ClassPhoto({ photoId, alt, className = '' }:
  { photoId: string; alt: string; className?: string }) {
  const [url, setUrl] = useState('')
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let live = true
    let objectUrl = ''
    setUrl(''); setFailed(false)
    apiBlob(`/class-photos/${photoId}/file`)
      .then((blob) => {
        if (!live) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
      })
      .catch(() => { if (live) setFailed(true) })
    return () => {
      live = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [photoId])

  if (failed) {
    return <div className={`class-photo missing ${className}`} role="img" aria-label={`${alt} (could not load)`}>🖼</div>
  }
  if (!url) return <div className={`class-photo loading ${className}`} aria-hidden="true" />
  return <img className={`class-photo ${className}`} src={url} alt={alt} />
}
