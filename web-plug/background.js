// 监听来自内容脚本（页面）和弹窗的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === 'RECORD_ACTION') {
        chrome.storage.local.get(['isRecording', 'framework', 'recordedCode'], (data) => {
            if (!data.isRecording) return;
            
            let codeLine = generateCode(data.framework, request.data);
            if (codeLine) {
                let newCode = (data.recordedCode || '') + codeLine + '\n';
                chrome.storage.local.set({ recordedCode: newCode });
            }
        });
    }
});

// 根据框架生成对应的代码
function generateCode(framework, actionData) {
    const { action, selector, value, url } = actionData;
    
    // 初始打开网页
    if (action === 'goto') {
        if (framework === 'selenium') return `driver.get("${url}")`;
        if (framework === 'drissionpage') return `page.get("${url}")`;
        if (framework === 'playwright') return `page.goto("${url}")`;
    }
    
    // 点击动作
    if (action === 'click') {
        if (framework === 'selenium') return `driver.find_element(By.CSS_SELECTOR, "${selector}").click()`;
        if (framework === 'drissionpage') return `page.ele("css:${selector}").click()`;
        if (framework === 'playwright') return `page.locator("${selector}").click()`;
    }
    
    // 输入文字动作
    if (action === 'input') {
        // 将输入内容中的引号转义，防止代码报错
        const safeValue = value.replace(/"/g, '\\"');
        if (framework === 'selenium') return `driver.find_element(By.CSS_SELECTOR, "${selector}").send_keys("${safeValue}")`;
        if (framework === 'drissionpage') return `page.ele("css:${selector}").input("${safeValue}")`;
        if (framework === 'playwright') return `page.locator("${selector}").fill("${safeValue}")`;
    }
    
    return null;
}