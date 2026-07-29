import { useId, useState } from 'react'

/**
 * Tooltip "Por que estou vendo isso?" — explica a razão da recomendação vinda
 * do campo `motivo` de `GET /feed/` (critério de aceitação da #47).
 *
 * Abre no hover, no foco por teclado e no clique/toque; fecha ao sair, ao
 * perder o foco ou com Esc. O clique só abre (nunca alterna): hover e foco
 * disparam antes do clique no mesmo gesto, e alternar faria o tooltip fechar
 * no mesmo movimento que o abriu. O clique também não pode borbulhar — o card
 * inteiro é clicável e abriria o modal do conteúdo.
 */
export function ReasonTooltip({ motivo }) {
  const [hover, setHover] = useState(false)
  const [fixado, setFixado] = useState(false)
  const id = useId()

  if (!motivo) return null

  const aberto = hover || fixado

  return (
    <span
      className="feed-reason"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <button
        type="button"
        className="feed-reason-trigger"
        aria-expanded={aberto}
        aria-describedby={aberto ? id : undefined}
        onFocus={() => setFixado(true)}
        onBlur={() => setFixado(false)}
        onKeyDown={(e) => {
          if (e.key === 'Escape') setFixado(false)
        }}
        onClick={(e) => {
          e.stopPropagation()
          setFixado(true)
        }}
      >
        Por que estou vendo isso?
      </button>
      {aberto && (
        <span role="tooltip" id={id} className="feed-reason-tooltip">
          {motivo}
        </span>
      )}
    </span>
  )
}
