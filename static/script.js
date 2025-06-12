// script.js (The Final, Publishable Version)
$(document).ready(function() {
    // --- 缓存DOM元素 ---
    const $loginSection = $('#login-section'), $gradesSection = $('#grades-section');
    const $allGradesContainer = $('#all-grades-container');
    const $loadingSpinner = $('#loading-spinner'), $welcomeSection = $('#welcome-section');
    const $userAvatar = $('#userAvatar'), $userNameDisplay = $('#userNameDisplay'), $userIdDisplay = $('#userIdDisplay');
    const $currentTermPassed = $('#currentTermPassed'), $currentTermProgress = $('#currentTermProgress'), $overallGpaValue = $('#overallGpaValue');

    // --- 核心渲染函数 ---
    const displayAllGrades = (allGrades) => {
        $allGradesContainer.empty();
        if (!allGrades || allGrades.length === 0) {
            $allGradesContainer.append('<p>暂无成绩数据。</p>'); return;
        }

        allGrades.forEach((termData, termIndex) => {
            const termId = `term-${termIndex}`;
            const isCurrentClass = termData.isCurrent ? 'is-current' : '';
            // [FINAL POLISH] Added wrapper for chevron and staggered animation delay
            const termCardHtml = `
                <div class="term-card ${isCurrentClass}" id="${termId}" style="animation-delay: ${termIndex * 70}ms">
                    <div class="term-header">
                        <div class="term-header-info">
                            ${termData.isCurrent ? '<span class="term-tag current">当前学期</span>' : ''}
                            ${termData.termLabel ? `<span class="term-tag">${termData.termLabel}</span>` : ''}
                            <span class="term-name">${termData.termName}</span>
                        </div>
                        <div class="term-chevron-wrapper">
                            <i class="icon chevron-right"></i>
                        </div>
                    </div>
                    <div class="term-content">
                        <div class="grades-list"></div>
                    </div>
                </div>
            `;
            $allGradesContainer.append(termCardHtml);

            const $gradesList = $(`#${termId} .grades-list`);
            if (termData.list && termData.list.length > 0) {
                termData.list.forEach((grade) => {
                    const displayScore = grade.isValidScore ? grade.courseScore : '未公布';
                    const isPassed = grade.isValidScore && parseFloat(grade.courseScore) >= 60;
                    const cardClass = grade.isValidScore ? (isPassed ? 'passed' : 'failed') : 'not-announced';
                    const gradeItemHtml = `
                        <div class="grade-item ${cardClass}">
                            <div class="card-main">
                                <div class="card-main-info">
                                    <p class="course-name">${grade.courseName || 'N/A'}</p>
                                    <p class="course-details-inline">学分: ${grade.credit || 'N/A'}</p>
                                </div>
                                <div class="card-main-action">
                                    <span class="score-value">${displayScore}</span>
                                </div>
                            </div>
                            <div class="card-details-extra">
                                <div>
                                    <div class="detail-row"><span class="detail-label">绩点</span><span class="detail-value">${grade.gradePoint || 'N/A'}</span></div>
                                    <div class="detail-row"><span class="detail-label">等级</span><span class="detail-value">${grade.levelName || 'N/A'}</span></div>
                                    <div class="detail-row"><span class="detail-label">考试类型</span><span class="detail-value">${grade.examTypeName || 'N/A'}</span></div>
                                    <div class="detail-row"><span class="detail-label">录入时间</span><span class="detail-value">${grade.operatetime || 'N/A'}</span></div>
                                </div>
                            </div>
                        </div>`;
                    $gradesList.append(gradeItemHtml);
                });
            }
        });
        $allGradesContainer.find('.term-card.is-current').addClass('is-expanded');
    };

    const handleLoginSuccess = (response) => {
        const { user_name, username, all_grades, overall_gpa, current_stats } = response;
        $userAvatar.text(user_name ? user_name.charAt(0) : 'Hi');
        $userNameDisplay.text(user_name || '同学');
        $userIdDisplay.text(`学号: ${username || '未知'}`);
        $('#welcomeMessage').text(`${user_name}，欢迎回来`);

        $currentTermPassed.text(current_stats.passed);
        $currentTermProgress.text(`${current_stats.announced} / ${current_stats.total}`);
        $overallGpaValue.text(overall_gpa || "N/A");

        displayAllGrades(all_grades);
        
        $loginSection.hide();
        $loadingSpinner.removeClass('animate-exit').addClass('animate-enter');
        
        setTimeout(() => {
            $loadingSpinner.removeClass('animate-enter').addClass('animate-exit');
            $welcomeSection.addClass('animate-enter');
            setTimeout(() => {
                $welcomeSection.removeClass('animate-enter').addClass('animate-exit');
                $gradesSection.show().css('opacity', 1);
            }, 1200);
        }, 500);
    };

    const initApp = () => {
        $loadingSpinner.addClass('animate-enter');
        $.ajax({
            url: '/api/auto_login_and_grades', method: 'POST',
            success: (res) => { if (res.success) handleLoginSuccess(res); },
            error: (xhr) => {
                $loadingSpinner.addClass('animate-exit');
                $loginSection.show();
                if (xhr.status !== 401) { $('#loginMessage').text('无法连接服务器').addClass('error').css('opacity', 1); } 
                else {
                    const res = xhr.responseJSON;
                    if (res && res.username_saved) $('#username').val(res.username_saved);
                }
            }
        });
    };

    $('#manualLoginBtn').on('click', function() {
        const username = $('#username').val().trim();
        const password = $('#password').val();
        if (!username || !password) { return; }
        $.ajax({
            url: '/api/manual_login_and_get_grades', method: 'POST', contentType: 'application/json',
            data: JSON.stringify({ username, password, save_info: $('#saveLoginInfo').is(':checked') }),
            success: (res) => { if (res.success) handleLoginSuccess(res); },
            error: (xhr) => { $('#loginMessage').text(xhr.responseJSON?.message || '请求失败').addClass('error').css('opacity', 1); }
        });
    });

    $('#logoutBtn').on('click', () => { $.post('/api/logout', () => window.location.reload()); });
    $gradesSection.on('click', '.term-header', function() { $(this).closest('.term-card').toggleClass('is-expanded'); });
    $gradesSection.on('click', '.grade-item', function(e) { e.stopPropagation(); $(this).toggleClass('expanded'); });

    initApp();
});
