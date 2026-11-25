import { useEffect, useRef } from 'react';

export function AmbientBackground() {
  const backgroundRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const background = backgroundRef.current;
    if (!background) return;

    let frame = 0;
    let previousScrollY = window.scrollY;
    let sceneOpacity = Math.min(0.12 + window.scrollY * 0.00072, 0.98);

    const updateScroll = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const currentScrollY = window.scrollY;
        sceneOpacity = Math.max(
          0.12,
          Math.min(0.98, sceneOpacity + (currentScrollY - previousScrollY) * 0.00072)
        );
        previousScrollY = currentScrollY;
        background.style.setProperty('--scene-opacity', sceneOpacity.toFixed(3));
      });
    };

    window.addEventListener('scroll', updateScroll, { passive: true });
    updateScroll();

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('scroll', updateScroll);
      background.style.removeProperty('--scene-opacity');
    };
  }, []);

  return (
    <div className="ambient-background" ref={backgroundRef} aria-hidden="true">
      <div className="ambient-landscape">
        <img
          className="ambient-landscape__image"
          src="/images/financial-documents-bg.jpg"
          alt=""
          draggable="false"
        />
      </div>
    </div>
  );
}
