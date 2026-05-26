import { motion, AnimatePresence } from 'framer-motion';

export interface DawnInfo {
  type: 'death' | 'safe';
  text: string;
}

export interface NightToast {
  icon: string;
  text: string;
}

interface PhaseOverlayProps {
  visible: boolean;
  dawnInfo?: DawnInfo | null;
  nightToast?: NightToast | null;
}

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
            transition={{ duration: 2, ease: 'easeInOut' }}
          >
            <motion.div
              className="phase-overlay-content"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              transition={{ duration: 1.5, ease: 'easeInOut', delay: 0.3 }}
            >
              <motion.div
                className="phase-overlay-icon"
                animate={{
                  rotate: [0, -10, 10, -5, 0],
                  scale: [1, 1.05, 1, 1.03, 1],
                }}
                transition={{
                  duration: 4,
                  ease: 'easeInOut',
                  repeat: Infinity,
                  repeatDelay: 1,
                }}
              >
                🌙
              </motion.div>
              <motion.div
                className="phase-overlay-text"
                animate={{ opacity: [0, 1] }}
                transition={{ duration: 1.5, ease: 'easeInOut', delay: 1 }}
              >
                天黑请闭眼
              </motion.div>
            </motion.div>
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
            transition={{ duration: 0.8, ease: 'easeInOut' }}
          >
            <motion.div
              className="phase-overlay-content"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              transition={{ duration: 0.6, ease: 'easeInOut', delay: 0.1 }}
            >
              <motion.div
                className="phase-overlay-icon dawn-icon"
                animate={{
                  rotate: [0, 15, -5, 0],
                  scale: [1, 1.1, 1, 1],
                }}
                transition={{ duration: 1.5, ease: 'easeInOut' }}
              >
                ☀️
              </motion.div>
              <motion.div
                className="phase-overlay-text"
                animate={{ opacity: [0, 1] }}
                transition={{ duration: 0.6, ease: 'easeInOut', delay: 0.3 }}
              >
                天亮了
              </motion.div>
            </motion.div>
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
            transition={{ duration: 0.5, ease: 'easeInOut' }}
          >
            <motion.div
              className="phase-overlay-content"
              initial={{ scale: 0.6, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.6, opacity: 0, y: -10 }}
              transition={{ duration: 0.4, ease: 'easeInOut' }}
            >
              <motion.div
                className="phase-overlay-icon"
                style={{ fontSize: 48 }}
                animate={{ scale: [1, 1.15, 1] }}
                transition={{ duration: 0.8, ease: 'easeInOut' }}
              >
                {nightToast.icon}
              </motion.div>
              <motion.div
                className="phase-overlay-text"
                style={{ fontSize: 22 }}
                animate={{ opacity: [0, 1] }}
                transition={{ duration: 0.4, ease: 'easeInOut', delay: 0.15 }}
              >
                {nightToast.text}
              </motion.div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

export function DawnBanner({ info, onDone }: { info: DawnInfo; onDone: () => void }) {
  return (
    <AnimatePresence onExitComplete={onDone}>
      <motion.div
        className={`dawn-banner ${info.type}`}
        initial={{ y: -60, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: -60, opacity: 0 }}
        transition={{ duration: 0.6, ease: 'easeInOut', delay: 0.5 }}
      >
        {info.text}
      </motion.div>
    </AnimatePresence>
  );
}
