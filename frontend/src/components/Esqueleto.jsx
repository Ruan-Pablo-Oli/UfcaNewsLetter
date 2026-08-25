/**
 * Espera com forma: em vez de "Carregando…", o desenho do que vai chegar.
 * A tela não salta quando o conteúdo entra, e a espera parece mais curta
 * porque já se vê a estrutura.
 */
export function Esqueleto({ linhas = 3, variante = 'card' }) {
  return (
    <div className="esqueleto-lista" aria-busy="true" aria-live="polite">
      <span className="sr-apenas">Carregando conteúdos…</span>
      {Array.from({ length: linhas }, (_, i) => (
        <div key={i} className={`esqueleto esqueleto-${variante}`}>
          <div className="esqueleto-linha esqueleto-meta" />
          <div className="esqueleto-linha esqueleto-titulo" />
          <div className="esqueleto-linha" />
          <div className="esqueleto-linha esqueleto-curta" />
        </div>
      ))}
    </div>
  )
}
