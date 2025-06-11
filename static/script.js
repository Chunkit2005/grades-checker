// script.js (Complete Updated Version for Redesign)
$(document).ready(function() {
    // --- 缓存DOM元素 ---
    const $usernameInput = $('#username'), $passwordInput = $('#password');
    const $manualLoginBtn = $('#manualLoginBtn'), $loginMessage = $('#loginMessage');
    const $saveLoginInfoCheckbox = $('#saveLoginInfo');
    const $loginSection = $('#login-section'), $gradesSection = $('#grades-section');
    const $gradesOutput = $('#gradesOutput');
    const $logoutBtn = $('#logoutBtn');
    const $loadingSpinner = $('#loading-spinner'), $welcomeSection = $('#welcome-section');
    const $welcomeMessage = $('#welcomeMessage');
    const $userAvatar = $('#userAvatar'), $userNameDisplay = $('#userNameDisplay');
    const $userIdDisplay = $('#userIdDisplay'), $greetingText = $('#greetingText');
    const $passedCoursesCount = $('#passedCoursesCount');
    const $takenCoursesCount = $('#takenCoursesCount');
    const $overallGpaValue = $('#overallGpaValue');

    // --- 辅助函数 ---
    const showLoginMessage = (msg, type = 'info') => {
        $loginMessage.removeClass('success error info').addClass(type).text(msg);
        $loginMessage.css({'opacity': msg ? 1 : 0, 'max-height': msg ? '70px' : '0'});
    };

    const toggleLoginElements = (enable) => {
        $usernameInput.prop('disabled', !enable);
        $passwordInput.prop('disabled', !enable);
        $manualLoginBtn.prop('disabled', !enable);
        $saveLoginInfoCheckbox.prop('disabled', !enable);
    };

    const getGreeting = () => {
        const hour = new Date().getHours();
        if (hour < 6) return "凌晨好"; if (hour < 12) return "上午好";
        if (hour < 14) return "中午好"; if (hour < 18) return "下午好";
        return "晚上好";
    };

    // --- 核心逻辑函数 ---
    const updateStatistics = (gradesData, overallGpa, courseCount) => {
        let passedCount = 0, takenCount = 0;
        gradesData.forEach(term => {
            term.list.forEach(grade => {
                if (grade.isValidScore) { takenCount++; if (parseFloat(grade.courseScore) >= 60) { passedCount++; } }
            });
        });
        $passedCoursesCount.text(passedCount);
        $takenCoursesCount.text(`${takenCount} / ${courseCount || '?'}`);
        const gpaToShow = (overallGpa && overallGpa.trim() !== "" && parseFloat(overallGpa) !== 0.0) ? overallGpa : "N/A";
        $overallGpaValue.text(gpaToShow);
    };

    const displayGrades = (gradesData) => {
        $gradesOutput.empty();
        if (!gradesData || gradesData.length === 0) {
            $gradesOutput.append('<p class="no-grades-message">未能获取到成绩数据。</p>');
            return;
        }

        gradesData.forEach(termData => {
            $gradesOutput.append(`<h3 class="term-title">${termData.termName}</h3>`);
            if (termData.list && termData.list.length > 0) {
                termData.list.forEach((grade, index) => {
                    const displayScore = grade.isValidScore ? grade.courseScore : '未公布';
                    const isPassed = grade.isValidScore && parseFloat(grade.courseScore) >= 60;
                    const cardClass = grade.isValidScore ? (isPassed ? 'passed' : 'failed') : 'not-announced';

                    // [REDESIGNED] HTML for grade item
                    const gradeItemHtml = `
                        <div class="grade-item ${cardClass}" style="transition-delay: ${index * 50}ms">
                            <div class="card-main">
                                <div class="card-main-info">
                                    <p class="course-name">${grade.courseName || 'N/A'}</p>
                                    <p class="course-details-inline">学分: ${grade.credit || 'N/A'}</p>
                                </div>
                                <div class="card-main-action">
                                    <span class="score-value">${displayScore}</span>
                                    <i class="icon chevron-right"></i>
                                </div>
                            </div>
                            <div class="card-details-extra">
                                <div class="detail-row"><span class="detail-label">绩点</span><span class="detail-value">${grade.gradePoint || 'N/A'}</span></div>
                                <div class="detail-row"><span class="detail-label">等级</span><span class="detail-value">${grade.levelName || 'N/A'}</span></div>
                                <div class="detail-row"><span class="detail-label">考试类型</span><span class="detail-value">${grade.examTypeName || 'N/A'}</span></div>
                                <div class="detail-row"><span class="detail-label">录入时间</span><span class="detail-value">${grade.operatetime || 'N/A'}</span></div>
                            </div>
                        </div>`;
                    $gradesOutput.append(gradeItemHtml);
                });
            }
        });
        
        setTimeout(() => $('.grade-item').addClass('is-visible'), 100);

        $gradesOutput.on('click', '.grade-item', function() {
            $(this).toggleClass('expanded');
            const $details = $(this).find('.card-details-extra');
            $details.css('max-height', $(this).hasClass('expanded') ? $details[0].scrollHeight + 'px' : '0');
        });
    };

    const handleLoginSuccess = (response) => {
        const { user_name, username, grades, overall_gpa, course_count } = response;
        $userAvatar.text(user_name ? user_name.charAt(0) : 'Hi');
        $userNameDisplay.text(user_name || '同学');
        $userIdDisplay.text(`学号: ${username || '未知'}`);
        $greetingText.text(getGreeting());
        $welcomeMessage.text(`${user_name}，欢迎回来`);
        $loginSection.hide();
        $loadingSpinner.removeClass('animate-exit').addClass('animate-enter');
        updateStatistics(grades, overall_gpa, course_count);
        displayGrades(grades);
        setTimeout(() => {
            $loadingSpinner.removeClass('animate-enter').addClass('animate-exit');
            $welcomeSection.addClass('animate-enter');
            setTimeout(() => {
                $welcomeSection.removeClass('animate-enter').addClass('animate-exit');
                $gradesSection.show().css('opacity', 1);
            }, 1200);
        }, 500);
    };

    // --- 事件绑定和初始化 ---
    const initApp = () => {
        $loadingSpinner.addClass('animate-enter');
        $.ajax({
            url: '/api/auto_login_and_grades', method: 'POST',
            success: (res) => {
                if (res.success) { handleLoginSuccess(res); } 
                else { $loadingSpinner.addClass('animate-exit'); $loginSection.show(); if (res.username_saved) $usernameInput.val(res.username_saved); }
            },
            error: () => { $loadingSpinner.addClass('animate-exit'); $loginSection.show(); showLoginMessage('无法连接服务器', 'error'); }
        });
    };

    $manualLoginBtn.on('click', function() {
        const username = $usernameInput.val().trim();
        const password = $passwordInput.val();
        if (!username || !password) { showLoginMessage('学号和密码不能为空！', 'error'); return; }
        showLoginMessage('正在登录...', 'info');
        toggleLoginElements(false);
        $.ajax({
            url: '/api/manual_login_and_get_grades', method: 'POST', contentType: 'application/json',
            data: JSON.stringify({ username, password, save_info: $saveLoginInfoCheckbox.is(':checked') }),
            success: (res) => {
                if (res.success) { handleLoginSuccess(res); } 
                else { showLoginMessage(res.message, 'error'); toggleLoginElements(true); }
            },
            error: (xhr) => { showLoginMessage(xhr.responseJSON?.message || '请求失败', 'error'); toggleLoginElements(true); }
        });
    });

    $logoutBtn.on('click', () => {
        $.post('/api/logout', () => { window.location.reload(); });
    });

    initApp();
});
