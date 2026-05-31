import { AnimatePresence, motion } from 'framer-motion';

interface PhaseOverlayProps {
  visible: boolean;
  dawnInfo?: { type: string; text: string } | null;
  nightToast?: { icon: string; text: string } | null;
}

export type NightToast = { icon: string; text: string };

export default function PhaseOverlay({ visible, dawnInfo, nightToast }: PhaseOverlayProps) {
  return (
    <>
      <AnimatePresence>
        {visible && (
          <motion.div
            className="phase-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="phase-overlay-content">
              <div className="phase-overlay-icon">🌙</div>
              <div className="phase-overlay-text">天黑请闭眼</div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {dawnInfo && (
          <motion.div
            className="phase-overlay dawn"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="phase-overlay-content">
              <div className="phase-overlay-icon dawn-icon">☀️</div>
              <div className="phase-overlay-text">天亮了</div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {nightToast && (
          <motion.div
            className="phase-overlay night-toast"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className="phase-overlay-content">
              <div className="phase-overlay-icon" style={{ fontSize: 36 }}>{nightToast.icon}</div>
              <div className="phase-overlay-text" style={{ fontSize: 20 }}>{nightToast.text}</div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
