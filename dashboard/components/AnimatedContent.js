import { Children, cloneElement, isValidElement, useEffect, useRef, useState } from "react";

const EASINGS = {
  "power3.out": "cubic-bezier(.22, 1, .36, 1)",
  "power2.out": "cubic-bezier(.25, .8, .25, 1)",
  "power1.out": "cubic-bezier(.3, .7, .4, 1)",
  linear: "linear",
};

export default function AnimatedContent({
  children,
  distance = 100,
  direction = "vertical",
  duration = 0.8,
  ease = "power3.out",
  blur = 0,
  stagger = 0.08,
  threshold = 0.1,
  className = "",
  as: Element = "div",
  style = {},
  ...rest
}) {
  const elementRef = useRef(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return undefined;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reducedMotion || typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return undefined;
    }

    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      setVisible(true);
      observer.unobserve(entry.target);
    }, { threshold: Math.max(0, Math.min(1, Number(threshold) || 0)) });

    observer.observe(element);
    return () => observer.disconnect();
  }, [threshold]);

  const travel = Math.max(0, Number(distance) || 0);
  const isHorizontal = direction === "horizontal" || direction === "left" || direction === "right";
  const signedTravel = direction === "left" || direction === "up" ? -travel : travel;
  const childrenWithStagger = Children.toArray(children).map((child, index) => {
    const childStyle = { "--animated-content-index": index };
    if (isValidElement(child) && typeof child.type === "string") {
      return cloneElement(child, {
        className: [child.props.className, "animated-content-child"].filter(Boolean).join(" "),
        style: { ...child.props.style, ...childStyle },
      });
    }
    return <div className="animated-content-child" style={childStyle} key={`animated-child-${index}`}>{child}</div>;
  });

  return <Element
    ref={elementRef}
    className={`animated-content${visible ? " is-visible" : ""}${className ? ` ${className}` : ""}`}
    style={{
      ...style,
      "--animated-content-x": isHorizontal ? `${signedTravel}px` : "0px",
      "--animated-content-y": isHorizontal ? "0px" : `${signedTravel}px`,
      "--animated-content-blur": `${Math.max(0, Number(blur) || 0)}px`,
      "--animated-content-duration": `${Math.max(0, Number(duration) || 0)}s`,
      "--animated-content-stagger": `${Math.max(0, Number(stagger) || 0)}s`,
      "--animated-content-ease": EASINGS[ease] || ease,
    }}
    {...rest}
  >{childrenWithStagger}</Element>;
}
