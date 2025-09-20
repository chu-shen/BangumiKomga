document.addEventListener('DOMContentLoaded', async function () {
    const formContainer = document.getElementById('config-form');
    const generateBtn = document.getElementById('generate-btn');
    const downloadBtn = document.getElementById('download-btn');
    const output = document.getElementById('output');
    const uploadBtn = document.getElementById('upload-btn');
    const fileInput = document.getElementById('config-file');

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
                        ${item.version ? `<span class="version">(v${item.version})</span>` : ''}
                    </label>
                    ${item.name === 'KOMGA_LIBRARY_LIST' || item.name === 'KOMGA_COLLECTION_LIST' ?
                    `<div class="help-text">由于安全限制，请手动输入</div>` : ''}
                    ${renderInput(item)}
                    ${item.info ? `<div class="help-text">${item.info}</div>` : ''}
                </div>
            `;
        });

        formContainer.innerHTML = formHTML;

        // 添加事件监听器
        configSchema.forEach(item => {
            if (item.type === 'list') {
                // 处理多选列表
                const checkboxes = document.querySelectorAll(`input[name="${item.name}"]`);
                checkboxes.forEach(checkbox => {
                    checkbox.addEventListener('change', updateConfigValue);
                });

                // 设置默认值
                if (Array.isArray(item.default) && item.default.length > 0) {
                    item.default.forEach(defaultValue => {
                        const checkbox = document.querySelector(`input[name="${item.name}"][value="${defaultValue}"]`);
                        if (checkbox) {
                            checkbox.checked = true;
                        }
                    });
                    updateConfigValue({ target: checkboxes[0] });
                }
            } else {
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
            }
        });

        validateForm();
    }

    // 根据类型渲染不同的输入字段
    function renderInput(item) {
        switch (item.type) {
            case 'boolean':
                return `
                        <input type="checkbox" name="${item.name}" ${item.default ? 'checked' : ''}>
                `;
            case 'password':
                return `<input type="password" name="${item.name}" placeholder="${item.default || ''}">`;
            case 'integer':
                return `<input type="number" name="${item.name}" value="${item.default || ''}">`;
            case 'url':
                return `<input type="url" name="${item.name}" placeholder="${item.default || ''}">`;
            case 'email':
                return `<input type="email" name="${item.name}" placeholder="${item.default || ''}">`;
            case 'list':
                if (item.allowed_values && item.allowed_values.length > 0) {
                    let checkboxes = item.allowed_values.map(value =>
                        `<div class="checkbox-item">
                                    <div for="${item.name}-${value}">${value}</div>
                                    <input type="checkbox" name="${item.name}" value="${value}" id="${item.name}-${value}">
                                </div>`
                    ).join('');
                    return `<div class="checkbox-group">${checkboxes}</div>`;
                } else {
                    return `<input type="text" name="${item.name}" placeholder="${item.default || ''}">`;
                }
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
        const item = configSchema.find(i => i.name === name);

        if (item && item.type === 'list') {
            // 处理多选列表
            const checkboxes = document.querySelectorAll(`input[name="${name}"]:checked`);
            if (input.type == 'checkbox') {
                configValues[name] = Array.from(checkboxes).map(cb => cb.value);
            } else {
                configValues[name] = JSON.parse(toJSON(input.value));
            }
        } else if (input.type === 'checkbox') {
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
                    configContent += `${item.name} = ${toPyhton(JSON.stringify(value)) }\n`;
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

    // 上传并解析配置文件
    uploadBtn.addEventListener('click', function () {
        if (!fileInput.files.length) {
            alert('请选择要上传的配置文件');
            return;
        }

        const file = fileInput.files[0];
        const reader = new FileReader();

        reader.onload = function (e) {
            try {
                const content = e.target.result;
                parseConfigFile(content);
            } catch (error) {
                alert('解析配置文件时出错: ' + error.message);
            }
        };

        reader.readAsText(file);
    });

    // 解析Python配置文件
    function parseConfigFile(content) {
        const lines = content.split('\n');
        const parsedConfig = {};

        lines.forEach(line => {
            // 跳过空行和注释
            if (!line.trim() || line.trim().startsWith('#')) {
                return;
            }

            // 解析配置行
            const match = line.match(/^(\w+)\s*=\s*(.+)$/);
            if (match) {
                const key = match[1];
                let value = match[2].trim();

                // 处理字符串值（移除引号）
                if (value.startsWith("'") && value.endsWith("'") ||
                    value.startsWith('"') && value.endsWith('"')) {
                    value = value.substring(1, value.length - 1);
                }
                // 处理布尔值
                else if (value === 'True' || value === 'False') {
                    value = value === 'True';
                }
                // 处理数字
                else if (!isNaN(value) && value !== '') {
                    value = Number(value);
                }
                // 处理列表
                else if (value.startsWith('[') && value.endsWith(']')) {
                    try {
                        // 先将Python风格的布尔值和None转换为JSON格式
                        let jsonStr = toJSON(value);

                        // 将单引号字符串转换为双引号字符串
                        jsonStr = jsonStr.replace(/'/g, '"');

                        value = JSON.parse(jsonStr);
                    } catch (e) {
                        console.error('解析失败:', e);
                    }
                }

                parsedConfig[key] = value;
            }
        });

        // 更新表单值
        configSchema.forEach(item => {
            if (parsedConfig.hasOwnProperty(item.name)) {
                const value = parsedConfig[item.name];
                configValues[item.name] = value;

                const input = document.querySelector(`[name="${item.name}"]`);
                if (input) {
                    if (item.type === 'list') {
                        if (item.allowed_values && item.allowed_values.length > 0) {
                            // 多选列表
                            const checkboxes = document.querySelectorAll(`input[name="${item.name}"]`);
                            checkboxes.forEach(checkbox => {
                                checkbox.checked = Array.isArray(value) ? value.includes(checkbox.value) : false;
                            });
                        } else {
                            // 文本列表
                            input.value = JSON.stringify(value);
                        }
                    } else if (input.type === 'checkbox') {
                        input.checked = Boolean(value);
                    } else {
                        input.value = value;
                    }
                }
            }
        });

        validateForm();
        alert('配置文件已成功加载！');
    }

    function toPyhton(value) {
        
        return value.replace(/: true/g, ': True')
            .replace(/: true,/g, ': True,')
            .replace(/: false/g, ': False')
            .replace(/: false,/g, ': False,')
            .replace(/: null/g, ': None')
            .replace(/: null,/g, ': None,')
            .replace(/true/g, 'True')
            .replace(/false/g, 'False')
            .replace(/null/g, 'None');
    }

    function toJSON(value) {
        return value.replace(/: True/g, ': true')
            .replace(/: True,/g, ': true,')
            .replace(/: False/g, ': false')
            .replace(/: False,/g, ': false,')
            .replace(/: None/g, ': null')
            .replace(/: None,/g, ': null,')
            .replace(/True/g, 'true')
            .replace(/False/g, 'false')
            .replace(/None/g, 'null');
    }
});