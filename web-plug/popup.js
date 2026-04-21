document.addEventListener('DOMContentLoaded', function() {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const clearBtn = document.getElementById('clearBtn');
    const frameworkSelect = document.getElementById('frameworkSelect');
    const codeOutput = document.getElementById('codeOutput');

    // 初始化加载
    chrome.storage.local.get(['isRecording', 'framework', 'recordedCode'], function(data) {
        if (data.isRecording) {
            startBtn.style.display = 'none';
            stopBtn.style.display = 'block';
        }
        if (data.framework) frameworkSelect.value = data.framework;
        if (data.recordedCode) codeOutput.value = data.recordedCode;
    });

    chrome.storage.onChanged.addListener(function(changes) {
        if (changes.recordedCode) {
            codeOutput.value = changes.recordedCode.newValue || "";
            codeOutput.scrollTop = codeOutput.scrollHeight; // 自动滚动到底部
        }
    });

    frameworkSelect.addEventListener('change', function() {
        chrome.storage.local.set({ framework: this.value });
    });

    // 点击开始录制
    startBtn.addEventListener('click', function() {
        chrome.storage.local.set({ isRecording: true, framework: frameworkSelect.value });
        startBtn.style.display = 'none';
        stopBtn.style.display = 'block';

        // 记录第一步：打开当前网页
        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
            if (tabs[0] && tabs[0].url) {
                chrome.runtime.sendMessage({
                    type: 'RECORD_ACTION',
                    data: { action: 'goto', url: tabs[0].url }
                });
            }
        });
    });

    stopBtn.addEventListener('click', function() {
        chrome.storage.local.set({ isRecording: false });
        startBtn.style.display = 'block';
        stopBtn.style.display = 'none';
    });

    clearBtn.addEventListener('click', function() {
        chrome.storage.local.set({ recordedCode: "" });
        codeOutput.value = "";
    });
});