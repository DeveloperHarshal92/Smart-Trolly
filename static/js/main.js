(() => {
  "use strict";

  const ready = (callback) => {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback, { once: true });
    } else {
      callback();
    }
  };

  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const pressEffect = (element) => {
    if (!element) return;
    element.animate(
      [
        { transform: "scale(1)" },
        { transform: "scale(0.97)", offset: 0.45 },
        { transform: "scale(1)" }
      ],
      { duration: 260, easing: "cubic-bezier(.2,.8,.2,1)" }
    );
  };

  const initGsap = () => {
    if (prefersReducedMotion || typeof window.gsap === "undefined") return;

    const gsap = window.gsap;
    const ScrollTrigger = window.ScrollTrigger;
    if (ScrollTrigger) gsap.registerPlugin(ScrollTrigger);

    const heroItems = gsap.utils.toArray(".js-hero-reveal");
    if (heroItems.length) {
      gsap.fromTo(
        heroItems,
        { y: 34, autoAlpha: 0 },
        { y: 0, autoAlpha: 1, duration: 0.9, stagger: 0.11, ease: "power3.out", clearProps: "transform" }
      );
      gsap.fromTo(
        ".js-vision-stage",
        { x: 55, y: 20, rotateY: -8, autoAlpha: 0 },
        { x: 0, y: 0, rotateY: 0, autoAlpha: 1, duration: 1.25, delay: 0.22, ease: "power3.out" }
      );
      gsap.to(".js-bounding-box", {
        xPercent: 2.2,
        yPercent: -1.8,
        scale: 1.025,
        duration: 2.4,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut"
      });
    }

    if (!ScrollTrigger) return;

    gsap.utils.toArray(".js-section-heading").forEach((heading) => {
      gsap.fromTo(
        heading,
        { y: 42, autoAlpha: 0 },
        {
          y: 0,
          autoAlpha: 1,
          duration: 0.85,
          ease: "power3.out",
          scrollTrigger: { trigger: heading, start: "top 84%", once: true }
        }
      );
    });

    const featureCards = gsap.utils.toArray(".js-feature-grid .feature-card");
    if (featureCards.length) {
      gsap.fromTo(
        featureCards,
        { y: 60, autoAlpha: 0 },
        {
          y: 0,
          autoAlpha: 1,
          duration: 0.9,
          stagger: 0.14,
          ease: "power3.out",
          scrollTrigger: { trigger: ".js-feature-grid", start: "top 78%", once: true }
        }
      );
    }

    const reviewCards = gsap.utils.toArray(".js-review-grid .review-card");
    if (reviewCards.length) {
      gsap.fromTo(
        reviewCards,
        { y: 46, autoAlpha: 0 },
        {
          y: 0,
          autoAlpha: 1,
          duration: 0.8,
          stagger: 0.12,
          ease: "power3.out",
          scrollTrigger: { trigger: ".js-review-grid", start: "top 80%", once: true }
        }
      );
    }

    gsap.utils.toArray(".js-proof-panel, .js-final-cta").forEach((panel) => {
      gsap.fromTo(
        panel,
        { y: 34, scale: 0.985, autoAlpha: 0 },
        {
          y: 0,
          scale: 1,
          autoAlpha: 1,
          duration: 0.95,
          ease: "power3.out",
          scrollTrigger: { trigger: panel, start: "top 82%", once: true }
        }
      );
    });

    const invoiceElements = gsap.utils.toArray(".js-invoice-reveal");
    if (invoiceElements.length) {
      gsap.fromTo(
        invoiceElements,
        { y: 28, autoAlpha: 0 },
        { y: 0, autoAlpha: 1, duration: 0.78, stagger: 0.1, ease: "power3.out" }
      );
    }

    gsap.to(".billing-ambient--left", {
      yPercent: 18,
      scrollTrigger: { trigger: ".billing-page", start: "top top", end: "bottom top", scrub: 1.2 }
    });
    gsap.to(".billing-ambient--right", {
      yPercent: -14,
      scrollTrigger: { trigger: ".billing-page", start: "top top", end: "bottom top", scrub: 1.2 }
    });
  };

  const initCardParallax = () => {
    if (prefersReducedMotion || !window.matchMedia("(pointer: fine)").matches) return;

    document.querySelectorAll("[data-parallax-card]").forEach((card) => {
      card.addEventListener("pointermove", (event) => {
        const rect = card.getBoundingClientRect();
        const x = (event.clientX - rect.left) / rect.width - 0.5;
        const y = (event.clientY - rect.top) / rect.height - 0.5;
        card.style.transform = `perspective(900px) rotateX(${y * -5}deg) rotateY(${x * 7}deg) translateY(-5px)`;
      });
      card.addEventListener("pointerleave", () => {
        card.style.transform = "perspective(900px) rotateX(0) rotateY(0) translateY(0)";
      });
    });
  };

  const initCheckoutControls = () => {
    const printButton = document.querySelector("[data-print-invoice]");
    printButton?.addEventListener("click", () => {
      pressEffect(printButton);
      window.setTimeout(() => window.print(), 150);
    });

    const checkoutForm = document.querySelector(".js-checkout-form");
    checkoutForm?.addEventListener("submit", (event) => {
      if (checkoutForm.dataset.submitting === "true" || !checkoutForm.checkValidity()) return;
      event.preventDefault();
      checkoutForm.dataset.submitting = "true";
      const button = checkoutForm.querySelector("button[type='submit']");
      pressEffect(button);
      if (button) {
        button.disabled = true;
        button.querySelector("span").textContent = "Creating secure order…";
      }
      window.setTimeout(() => checkoutForm.submit(), 240);
    });

    const clearForm = document.querySelector("[data-clear-cart]");
    clearForm?.addEventListener("submit", (event) => {
      if (clearForm.dataset.submitting === "true") return;
      event.preventDefault();
      if (!window.confirm("Clear every detected item from this trolley session?")) return;
      clearForm.dataset.submitting = "true";
      const button = clearForm.querySelector("button");
      pressEffect(button);
      window.setTimeout(() => clearForm.submit(), 220);
    });

    document.querySelectorAll(".console-button, .tech-button").forEach((button) => {
      button.addEventListener("pointerdown", () => pressEffect(button));
    });
  };

  const initVideoStream = () => {
    const feed = document.getElementById("video-feed");
    const status = document.getElementById("stream-status");
    const retry = document.querySelector("[data-retry-stream]");
    if (!feed || !status) return;

    feed.addEventListener("load", () => {
      status.className = "stream-pill is-live";
      status.textContent = "LIVE";
    });
    feed.addEventListener("error", () => {
      status.className = "stream-pill is-offline";
      status.textContent = "CAMERA OFFLINE";
    });
    retry?.addEventListener("click", () => {
      status.className = "stream-pill";
      status.textContent = "RECONNECTING";
      feed.src = `${feed.dataset.streamUrl}?t=${Date.now()}`;
    });
  };

  const initUploadPreview = () => {
    const form = document.querySelector("[data-upload-form]");
    if (!form) return;
    const input = form.querySelector("[data-upload-input]");
    const preview = form.querySelector("[data-upload-preview]");
    const prompt = form.querySelector("[data-upload-prompt]");
    const zone = form.querySelector("[data-upload-zone]");
    const submit = form.querySelector("[data-upload-submit]");
    const reset = form.querySelector("[data-upload-reset]");
    const filename = form.querySelector("[data-upload-name]");
    let objectUrl = null;

    const clear = () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = null;
      input.value = "";
      preview.removeAttribute("src");
      preview.classList.remove("is-visible");
      prompt.hidden = false;
      zone.classList.remove("has-file");
      submit.disabled = true;
      reset.disabled = true;
      filename.textContent = "No image selected.";
    };

    input.addEventListener("change", () => {
      const file = input.files?.[0];
      if (!file) return clear();
      if (!file.type.startsWith("image/")) {
        clear();
        filename.textContent = "Choose a valid JPG or PNG image.";
        return;
      }
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = URL.createObjectURL(file);
      preview.src = objectUrl;
      preview.classList.add("is-visible");
      prompt.hidden = true;
      zone.classList.add("has-file");
      submit.disabled = false;
      reset.disabled = false;
      filename.textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB`;
    });
    reset.addEventListener("click", clear);
  };
  const initRazorpayCheckout = () => {
    const checkout = document.querySelector("[data-razorpay-checkout]");
    if (!checkout) return;

    const errorBox = document.getElementById("payment-error");
    const payButton = document.querySelector("[data-open-razorpay]");
    const showError = (message) => {
      if (!errorBox) return;
      errorBox.textContent = message;
      errorBox.classList.remove("d-none");
    };

    if (typeof window.Razorpay === "undefined") {
      showError("Razorpay could not load. Check your internet connection and try again.");
      if (payButton) payButton.disabled = true;
      return;
    }

    const razorpay = new window.Razorpay({
      key: checkout.dataset.key,
      amount: Number(checkout.dataset.amount),
      currency: "INR",
      name: "Smart Trolley",
      description: "Smart-Mart retail invoice",
      order_id: checkout.dataset.orderId,
      prefill: {
        name: checkout.dataset.customerName,
        email: checkout.dataset.customerEmail
      },
      handler: (response) => {
        document.getElementById("razorpay-payment-id").value = response.razorpay_payment_id;
        document.getElementById("razorpay-order-id").value = response.razorpay_order_id;
        document.getElementById("razorpay-signature").value = response.razorpay_signature;
        document.getElementById("payment-callback-form").submit();
      },
      modal: {
        ondismiss: () => showError("Payment window closed. No payment was processed.")
      },
      theme: { color: "#4F46E5" }
    });

    razorpay.on("payment.failed", (response) => {
      showError(response.error.description || "Payment failed. Please try again.");
    });

    payButton?.addEventListener("click", () => {
      errorBox?.classList.add("d-none");
      razorpay.open();
    });

    window.requestAnimationFrame(() => razorpay.open());
  };

  ready(() => {
    initGsap();
    initCardParallax();
    initCheckoutControls();
    initVideoStream();
    initUploadPreview();
    initRazorpayCheckout();
  });
})();