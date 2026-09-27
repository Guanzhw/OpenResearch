import { m } from "../paraglide/messages.js";
import { ltr } from "../i18n";
import { getLocale } from "../paraglide/runtime.js";
import { fmtDuration, fmtTokens, type ContextUsage } from "../api";
import { usePopover } from "./ModelPicker";
import { ProgressBar } from "./ProgressBar";

/** Amber ≥80%, red ≥95% — mirrors Claude Desktop's context meter. */
function tone(pct: number): string {
  if (pct >= 95) return "var(--accent-red)";
  if (pct >= 80) return "var(--accent-amber)";
  return "var(--accent)";
}

const RING_R = 6.5;
const RING_C = 2 * Math.PI * RING_R;

/** Composer meter: how much of the model's context window this session has
 * used, drawn as a small progress ring (token-count text when the window is
 * unknown). Hidden until the harness first reports usage; the popover holds
 * the breakdown. */
export function ContextMeter({ usage }: { usage?: ContextUsage }) {
  if (!usage || (usage.usedTokens <= 0 && !usage.codexSessionUsage)) return null;
  return <VisibleContextMeter usage={usage} />;
}

function VisibleContextMeter({ usage }: { usage: ContextUsage }) {
  const { open, setOpen, ref } = usePopover();
  const { usedTokens, contextWindow } = usage;
  const codexSessionUsage = usage.codexSessionUsage;
  const approvalPath = codexSessionUsage?.approvalPath;
  const hasContextUsage = usedTokens > 0;
  const pct =
    hasContextUsage && contextWindow && contextWindow > 0
      ? Math.min(100, Math.round((usedTokens / contextWindow) * 100))
      : null;
  const fill = pct === null ? "var(--accent)" : tone(pct);
  const percent = pct === null
    ? ""
    : new Intl.NumberFormat(getLocale(), { style: "percent" }).format(pct / 100);

  return (
    <div className="option-picker relative inline-flex shrink-0" ref={ref}>
      <button
        type="button"
        className={`${pct === null ? "inline-flex h-8 items-center rounded-md px-1 transition-[background,color] duration-150 ease-standard hover:bg-surface" : "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-text transition-[background,color] duration-150 ease-standard hover:bg-surface"} composer-bare context-ring text-sm text-text`}
        title={hasContextUsage ? (codexSessionUsage ? m.context_meter_summary_title() : m.context_meter_context_window_used()) : m.context_meter_session_totals()}
        onClick={() => setOpen((v) => !v)}
      >
        {!hasContextUsage ? (
          <span aria-hidden="true">∑</span>
        ) : pct === null ? (
          fmtTokens(usedTokens)
        ) : (
          <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
            <circle
              cx="8"
              cy="8"
              r={RING_R}
              fill="none"
              stroke="var(--border)"
              strokeWidth="2.5"
           />
            <circle
              cx="8"
              cy="8"
              r={RING_R}
              fill="none"
              stroke={fill}
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeDasharray={`${(RING_C * Math.max(pct, 2)) / 100} ${RING_C}`}
              transform="rotate(-90 8 8)"
           />
          </svg>
        )}
      </button>
      {open && (
        <div className="option-menu absolute bottom-[calc(100%_+_8px)] start-0 max-h-95 flex flex-col bg-background border border-border rounded-lg shadow-menu z-50 overflow-hidden min-w-47.5 [&.align-right]:start-auto [&.align-right]:end-0 [&.drop-down]:bottom-auto [&.drop-down]:top-[calc(100%_+_4px)] [&.session-menu]:start-auto [&.session-menu]:end-1.5 [&.session-menu]:top-[calc(100%_-_2px)] [&.session-menu]:min-w-35 align-right context-meter-menu w-70 pt-2.5 px-3 pb-3 [&_.progress]:mt-2 [&_.progress]:mx-0 [&_.progress]:mb-0 [&_.progress-track]:h-[5px] [&_.progress-track]:border-0 [&_.progress-track]:bg-border">
          {hasContextUsage && (
            <div className="context-meter-section">
              <div className="context-meter-head flex justify-between items-baseline gap-3 text-sm text-muted">
                <span>{m.context_meter_context_window()}</span>
                <span className="context-meter-value text-text tabular-nums">
                  {pct === null
                    ? m.context_meter_tokens({ value: ltr(fmtTokens(usedTokens)) })
                    : m.context_meter_usage({ used: ltr(fmtTokens(usedTokens)), total: ltr(fmtTokens(contextWindow!)), percent: ltr(percent) })}
                </span>
              </div>
              {pct !== null && (
                <ProgressBar value={usedTokens} max={contextWindow!} fillColor={fill} />
              )}
            </div>
          )}
          {codexSessionUsage && (
            <div className={`${hasContextUsage ? "mt-3 border-t border-border pt-2.5" : ""} context-meter-session text-sm`}>
              <div className="context-meter-head mb-1 text-muted">{m.context_meter_session_totals()}</div>
              <div className="text-text tabular-nums">
                {codexSessionUsage.cumulativeTokens !== undefined
                  ? m.context_meter_cumulative_tokens({ value: ltr(fmtTokens(codexSessionUsage.cumulativeTokens)) })
                  : m.context_meter_cumulative_unavailable()}
              </div>
              {codexSessionUsage.cumulativeInputTokens !== undefined && (
                <div className="text-text tabular-nums">
                  {m.context_meter_cumulative_input({ value: ltr(fmtTokens(codexSessionUsage.cumulativeInputTokens)) })}
                </div>
              )}
              {codexSessionUsage.cumulativeCachedInputTokens !== undefined && (
                <div className="text-text tabular-nums">
                  {m.context_meter_cumulative_cached_input({ value: ltr(fmtTokens(codexSessionUsage.cumulativeCachedInputTokens)) })}
                </div>
              )}
              {codexSessionUsage.cumulativeOutputTokens !== undefined && (
                <div className="text-text tabular-nums">
                  {m.context_meter_cumulative_output({ value: ltr(fmtTokens(codexSessionUsage.cumulativeOutputTokens)) })}
                </div>
              )}
              <div className="text-text">
                {m.context_meter_approval_path({
                  value: ltr(
                    approvalPath === "auto_review"
                      ? m.context_meter_approval_auto_review()
                      : approvalPath === "user"
                        ? m.context_meter_approval_user()
                        : approvalPath === "disabled"
                          ? m.context_meter_approval_disabled()
                          : m.context_meter_approval_unknown(),
                  ),
                })}
              </div>
              <div className="text-text tabular-nums">
                {codexSessionUsage.elapsedMs !== undefined
                  ? m.context_meter_elapsed({ value: ltr(fmtDuration(codexSessionUsage.elapsedMs)) })
                  : m.context_meter_elapsed_unavailable()}
              </div>
              {(approvalPath === "auto_review" || codexSessionUsage.autoReviewUsageUnavailable) && (
                <div className="text-text tabular-nums">
                  {m.context_meter_auto_review_usage_unavailable()}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
