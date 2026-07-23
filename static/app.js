const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const queue = document.getElementById("queue");

const microCrop = document.getElementById("microCrop");
const cropPercent = document.getElementById("cropPercent");
const speedFactor = document.getElementById("speedFactor");
const crf = document.getElementById("crf");

const cropVal = document.getElementById("cropVal");
const speedVal = document.getElementById("speedVal");
const crfVal = document.getElementById("crfVal");

cropPercent.addEventListener("input", () => (cropVal.textContent = `${cropPercent.value}%`));
speedFactor.addEventListener("input", () => (speedVal.textContent = `${parseFloat(speedFactor.value).toFixed(3)}x`));
crf.addEventListener("input", () => (crfVal.textContent = crf.value));

["dragenter", "dragover"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);
dropzone.addEventListener("drop", (e) => {
  const files = e.dataTransfer.files;
  if (files.length) handleFiles(files);
});
fileInput.addEventListener("change", (e) => {
  if (e.target.files.length) handleFiles(e.target.files);
});

function handleFiles(files) {
  Array.from(files).forEach(uploadFile);
}

function uploadFile(file) {
  const jobEl = document.createElement("div");
  jobEl.className = "job";
  jobEl.innerHTML = `
    <div class="name">${file.name}</div>
    <div class="bar-bg"><div class="bar-fill"></div></div>
    <div class="msg">Mengupload...</div>
  `;
  queue.prepend(jobEl);

  const bar = jobEl.querySelector(".bar-fill");
  const msg = jobEl.querySelector(".msg");

  const formData = new FormData();
  formData.append("video", file);
  formData.append("micro_crop", microCrop.checked ? "true" : "false");
  formData.append("crop_percent", cropPercent.value);
  formData.append("speed_factor", speedFactor.value);
  formData.append("crf", crf.value);

  fetch("/upload", { method: "POST", body: formData })
    .then((r) => r.json())
    .then((data) => {
      if (data.error) {
        jobEl.classList.add("error");
        msg.textContent = data.error;
        return;
      }
      pollStatus(data.job_id, jobEl, bar, msg);
    })
    .catch(() => {
      jobEl.classList.add("error");
      msg.textContent = "Upload gagal, cek koneksi ke server.";
    });
}

function pollStatus(jobId, jobEl, bar, msg) {
  const interval = setInterval(() => {
    fetch(`/status/${jobId}`)
      .then((r) => r.json())
      .then((job) => {
        bar.style.width = `${job.progress || 0}%`;
        msg.textContent = job.message || job.status;

        if (job.status === "done") {
          clearInterval(interval);
          const link = document.createElement("a");
          link.href = `/download/${job.output_file}`;
          link.className = "download";
          link.textContent = "⬇ Download video bersih";
          link.setAttribute("download", "");
          jobEl.appendChild(link);
        } else if (job.status === "error") {
          clearInterval(interval);
          jobEl.classList.add("error");
        }
      })
      .catch(() => clearInterval(interval));
  }, 800);
}
