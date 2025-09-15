document.addEventListener('DOMContentLoaded', async function () {
    const formContainer = document.getElementById('config-form');
    const generateBtn = document.getElementById('generate-btn');
    const downloadBtn = document.getElementById('download-btn');
    const output = document.getElementById('output');

    let configSchema = [];
    let configValues = {};

    // 加载配置schema
    try {
        const response = await fetch('config_schema.json');
        configSchema = await response.json();
        renderForm();
    } catch (error) {
        formContainer.innerHTML = `<p class="error">加载配置schema失败: ${error.message}</p>`;
    }

    // 渲染表单
    function renderForm() {
        let formHTML = '';

        configSchema.forEach(item => {
            formHTML += `
                <div class="form-group">
                    <label>
                        ${item.prompt}
                        ${item.required ? '<span class="required">*</span>' : ''}
                    </label>
                    ${renderInput(item)}
                    ${item.info ? `<div class="help-text">${item.info}</div>` : ''}
                </div>
            `;
        });

        formContainer.innerHTML = formHTML;

        // 添加事件监听器
        configSchema.forEach(item => {
            const input = document.querySelector(`[name="${item.name}"]`);
            if (input) {
                input.addEventListener('change', updateConfigValue);
                input.addEventListener('input', updateConfigValue);

                // 设置默认值
                if (item.default !== undefined && item.default !== null && item.default !== '') {
                    if (input.type === 'checkbox') {
                        input.checked = item.default;
                    } else {
                        input.value = item.default;
                    }
                    updateConfigValue({ target: input });
                }
            }
        });

        validateForm();
    }

    // 根据类型渲染不同的输入字段
    function renderInput(item) {
        switch (item.type) {
            case 'boolean':
                return `
                    <label class="checkbox">
                        <input type="checkbox" name="${item.name}" ${item.default ? 'checked' : ''}>
                        启用
                    </label>
                `;
            case 'password':
                return `<input type="password" name="${item.name}" placeholder="${item.default || ''}">`;
            case 'integer':
                return `<input type="number" name="${item.name}" value="${item.default || ''}">`;
            case 'url':
                return `<input type="url" name="${item.name}" placeholder="${item.default || ''}">`;
            case 'email':
                return `<input type="email" name="${item.name}" placeholder="${item.default || ''}">`;
            default:
                if (item.allowed_values && item.allowed_values.length > 0) {
                    let options = item.allowed_values.map(value =>
                        `<option value="${value}" ${value === item.default ? 'selected' : ''}>${value}</option>`
                    ).join('');
                    return `<select name="${item.name}">${options}</select>`;
                } else {
                    return `<input type="text" name="${item.name}" placeholder="${item.default || ''}">`;
                }
        }
    }

    // 更新配置值
    function updateConfigValue(event) {
        const input = event.target;
        const name = input.name;

        if (input.type === 'checkbox') {
            configValues[name] = input.checked;
        } else {
            configValues[name] = input.value;
        }

        validateForm();
    }

    // 简单验证
    function validateForm() {
        const requiredFields = configSchema.filter(item => item.required);
        const allRequiredFilled = requiredFields.every(item => {
            const value = configValues[item.name];
            return value !== undefined && value !== null && value !== '';
        });

        generateBtn.disabled = !allRequiredFilled;
    }

    // 生成配置
    generateBtn.addEventListener('click', function () {
        let configContent = `# 由 BangumiKomga 网页配置生成器生成\n# 生成时间: ${new Date().toLocaleString()}\n\n`;

        configSchema.forEach(item => {
            const value = configValues[item.name] !== undefined ? configValues[item.name] : item.default;

            if (typeof value === 'boolean') {
                configContent += `${item.name} = ${value ? 'True' : 'False'}\n`;
            } else if (typeof value === 'number') {
                configContent += `${item.name} = ${value}\n`;
            } else if (Array.isArray(value)) {
                configContent += `${item.name} = ${JSON.stringify(value)}\n`;
            } else {
                configContent += `${item.name} = '${value}'\n`;
            }
        });

        output.textContent = configContent;
        output.classList.remove('hidden');
        downloadBtn.disabled = false;
    });

    // 下载配置
    downloadBtn.addEventListener('click', function () {
        const configContent = output.textContent;
        const blob = new Blob([configContent], { type: 'text/x-python' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');

        a.href = url;
        a.download = 'config.py';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });
});