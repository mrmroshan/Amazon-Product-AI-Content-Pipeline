document.addEventListener('DOMContentLoaded', () => {
    fetchJobs();
    // Auto-refresh queue every 5 seconds
    setInterval(fetchJobs, 5000);

    const startBtn = document.getElementById('startBtn');
    startBtn.addEventListener('click', triggerJob);
});

function getBadgeClass(status) {
    const s = status.toLowerCase();
    return `badge-status status-${s}`;
}

let jobsData = {};

async function fetchJobs() {
    try {
        const response = await fetch('/api/jobs');
        const data = await response.json();
        
        const tbody = document.getElementById('jobsTableBody');
        tbody.innerHTML = '';
        
        data.jobs.forEach(job => {
            jobsData[job.asin] = job;
            const tr = document.createElement('tr');
            
            // Format datetime locally if needed, here just basic string
            const updated = new Date(job.updated_at).toLocaleTimeString();
            
            let actionHtml = '';
            if (job.status === 'AWAITING_REVIEW') {
                actionHtml = `<button class="btn btn-sm btn-outline-warning" onclick="openReviewModal('${job.asin}')"><i class="fas fa-images"></i> Review Images</button>`;
            } else if (job.status === 'COMPLETED') {
                actionHtml = `<button class="btn btn-sm btn-success" onclick="triggerQA('${job.asin}')"><i class="fas fa-check-double"></i> Run QA Sentry</button>`;
            } else if (job.status === 'FAILED' || job.status === 'QA_FAILED') {
                actionHtml = `<button class="btn btn-sm btn-outline-danger" onclick="showError('${job.asin}')"><i class="fas fa-exclamation-triangle"></i> View Error</button>`;
            } else if (job.video_url) {
                actionHtml = `<a href="${job.video_url}" target="_blank" class="btn btn-sm btn-outline-info"><i class="fas fa-play"></i> Watch Preview</a>`;
            } else {
                actionHtml = `<span class="text-muted"><i class="fas fa-hourglass-half"></i> Processing</span>`;
            }

            tr.innerHTML = `
                <td class="fw-bold">${job.asin}</td>
                <td><span class="${getBadgeClass(job.status)}">${job.status}</span></td>
                <td>${updated}</td>
                <td>${actionHtml}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Failed to fetch jobs:", err);
    }
}

let currentErrorText = "";

function showError(asin) {
    const job = jobsData[asin];
    currentErrorText = job.error_log || "Unknown Error. Check backend logs.";
    
    document.getElementById('errorModalText').textContent = currentErrorText;
    
    const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
    errorModal.show();
}

function copyErrorToClipboard() {
    navigator.clipboard.writeText(currentErrorText).then(() => {
        alert("Error copied to clipboard!");
    }).catch(err => {
        console.error("Failed to copy:", err);
    });
}

async function triggerJob() {
    const input = document.getElementById('asinInput');
    const alertBox = document.getElementById('triggerAlert');
    const asin = input.value.trim();
    
    if (!asin) return;
    
    try {
        const btn = document.getElementById('startBtn');
        btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Triggering...`;
        btn.disabled = true;

        const res = await fetch('/api/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ asin: asin })
        });
        
        if (res.ok) {
            input.value = '';
            alertBox.style.display = 'block';
            alertBox.textContent = `Job for ${asin} queued successfully!`;
            setTimeout(() => alertBox.style.display = 'none', 3000);
            fetchJobs();
        }
    } catch (err) {
        console.error(err);
    } finally {
        const btn = document.getElementById('startBtn');
        btn.innerHTML = `Build Content`;
        btn.disabled = false;
    }
}

async function triggerQA(asin) {
    if (!confirm(`Trigger QA Sentry for ASIN: ${asin}?`)) return;
    
    try {
        const res = await fetch(`/api/qa/${asin}`, { method: 'POST' });
        const data = await res.json();
        
        if (data.status === 'QA_PASSED') {
            alert(`✅ PASS: ${data.reason}`);
        } else {
            alert(`❌ FAILED: ${data.reason}`);
        }
        fetchJobs();
    } catch (err) {
        console.error("QA Failed:", err);
        alert("QA API Error");
    }
}

let activeReviewAsin = "";
let currentReviewSelections = {};

function openReviewModal(asin) {
    activeReviewAsin = asin;
    currentReviewSelections = {};
    const job = jobsData[asin];
    
    document.getElementById('reviewAsinBadge').textContent = asin;
    
    const baseImg = document.getElementById('reviewBaseImage');
    baseImg.src = job.product_image_url || 'https://via.placeholder.com/500?text=No+Ref+Image';
    
    const container = document.getElementById('scenesContainer');
    container.innerHTML = '';
    
    if(!job.scenes_json) {
        container.innerHTML = '<p class="text-danger">No scene data found!</p>';
        return;
    }
    
    let scenes = [];
    try {
        scenes = JSON.parse(job.scenes_json);
    } catch(e) {
        container.innerHTML = '<p class="text-danger">Failed to parse JSON.</p>';
        return;
    }
    
    scenes.forEach(scene => {
        const sceneBlock = document.createElement('div');
        sceneBlock.className = 'glass-card p-3 mb-4';
        
        let variantsHtml = '';
        scene.variants.forEach((imgUrl, i) => {
            variantsHtml += `
                <div class="col-4">
                    <img src="${imgUrl}" 
                         class="img-fluid rounded border border-secondary scene-variant" 
                         style="cursor: pointer; opacity: 0.6; transition: 0.3s;"
                         onclick="selectVariant('${scene.scene_id}', '${imgUrl}', this)"
                         data-scene="${scene.scene_id}">
                </div>
            `;
        });
        
        sceneBlock.innerHTML = `
            <div class="mb-2">
                <span class="badge bg-primary">Scene ${parseInt(scene.scene_id) + 1}</span>
                <p class="fst-italic mt-2 text-info">"${scene.description}"</p>
            </div>
            <div class="row">
                ${variantsHtml}
            </div>
        `;
        container.appendChild(sceneBlock);
    });
    
    const reviewModal = new bootstrap.Modal(document.getElementById('reviewModal'));
    reviewModal.show();
}

function selectVariant(sceneId, imgUrl, el) {
    currentReviewSelections[sceneId] = imgUrl;
    
    // reset visuals
    const group = document.querySelectorAll(`img[data-scene="${sceneId}"]`);
    group.forEach(img => {
        img.classList.remove('border-success', 'border-3');
        img.classList.add('border-secondary');
        img.style.opacity = '0.6';
    });
    
    // highlight selected
    el.classList.remove('border-secondary');
    el.classList.add('border-success', 'border-3');
    el.style.opacity = '1.0';
}

async function approveSelectedImages() {
    const job = jobsData[activeReviewAsin];
    let scenes = JSON.parse(job.scenes_json);
    
    if(Object.keys(currentReviewSelections).length < scenes.length) {
        alert("Please select exactly ONE image variant for every scene before approving!");
        return;
    }
    
    try {
        const btn = document.querySelector('#reviewModal .btn-success');
        btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Submitting...`;
        btn.disabled = true;

        const res = await fetch(`/api/approve_images/${activeReviewAsin}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ selected_images: currentReviewSelections })
        });
        
        if (res.ok) {
            const reviewModal = bootstrap.Modal.getInstance(document.getElementById('reviewModal'));
            reviewModal.hide();
            fetchJobs();
        } else {
            const data = await res.json();
            alert("Approval Failed: " + data.detail);
        }
    } catch (err) {
        console.error(err);
        alert("Network Error");
    } finally {
        const btn = document.querySelector('#reviewModal .btn-success');
        btn.innerHTML = `<i class="fas fa-check"></i> Approve & Render`;
        btn.disabled = false;
    }
}
