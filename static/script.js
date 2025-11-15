const headerTitle = document.getElementById('headerTitle');
const headerText = document.getElementById('headerText'); 
const settingsBtn = document.getElementById('settingsBtn');
const settingsPanel = document.getElementById('settingsPanel');
const userNameInput = document.getElementById('userNameInput');
const saveUserName = document.getElementById('saveUserName');
const messageBox = document.getElementById('messageBox');

const diaryCarousel = document.getElementById('diaryCarousel');
const musicContent = document.getElementById('musicContent');

// 사이드바 엘리먼트
const bookmarkBtn = document.getElementById('bookmarkBtn');
const sidebarPanel = document.getElementById('sidebarPanel');
const sidebarList = document.getElementById('sidebarList');
const closeSidebar = document.getElementById('closeSidebar');

let allDiaries = [];
let currentIndex = 0;

function showMessage(text, duration = 2000) {
    messageBox.textContent = text;
    messageBox.style.display = 'block';
    setTimeout(() => {
        messageBox.style.display = 'none';
    }, duration);
}

const datePickers = {};

// 사이드바 목록 렌더링
function updateSidebarList() {
    sidebarList.innerHTML = '';

    const reversedDiaries = [...allDiaries].sort((a, b) => b.date.localeCompare(a.date));
    const currentDate = allDiaries[currentIndex] ? allDiaries[currentIndex].date : null;
    const shouldFade = allDiaries.length > 7;

    reversedDiaries.forEach((it) => {
        const div = document.createElement('div');
        div.className = 'sidebar-item';

        const originalIdx = allDiaries.findIndex(d => d.date === it.date); 
        
        if (it.date === currentDate) {
            div.classList.add('current');
        }
        
        let titleText = it.title || (String(it.id).startsWith('temp-') || it.id === 'new'
            ? '(임시 새 일기)' : '(제목 없음)');
        
        const deleteBtnHtml = it.id !== 'new' && !String(it.id).startsWith('temp-')
            ? `<button class="sidebar-delete-btn" data-id="${it.id}" title="일기 삭제">🗑️</button>`
            : '';
        
        div.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                <div style="flex: 1; min-width: 0;">
                    <span class="sidebar-date">${it.date.replace(/-/g, '. ')}</span>
                    <span style="font-weight: 500; font-size: 15px; display: block;">${titleText}</span>
                </div>
                ${deleteBtnHtml}
            </div>
        `;
        
        if (shouldFade && originalIdx !== -1) {
            const distance = Math.abs(currentIndex - originalIdx);
            let opacity = 1.0;

            if (distance > 0) {
                opacity = Math.max(0.4, 1.0 - (distance * 0.2)); 
            }
            div.style.opacity = opacity;
        }

        div.onclick = (e) => {
            // 삭제 버튼 클릭 시에는 일기 전환하지 않음
            if (e.target.classList.contains('sidebar-delete-btn')) {
                return;
            }
            if (originalIdx !== -1) {
                currentIndex = originalIdx;
                updateCarouselPosition();
                sidebarPanel.classList.remove('show');
            }
        };
        
        // 삭제 버튼 이벤트 리스너
        const deleteBtn = div.querySelector('.sidebar-delete-btn');
        if (deleteBtn) {
            deleteBtn.onclick = async (e) => {
                e.stopPropagation();
                const diaryId = deleteBtn.dataset.id;
                
                if (!confirm('정말 이 일기를 삭제하시겠습니까?')) {
                    return;
                }
                
                try {
                    const res = await fetch('/diary/delete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ id: parseInt(diaryId) })
                    });
                    
                    if (!res.ok) throw new Error('서버 오류');
                    
                    await loadRecent();
                    showMessage('일기가 삭제되었습니다.');
                    
                } catch (e) {
                    console.error(e);
                    showMessage('삭제 실패! 서버 확인 필요');
                }
            };
        }
        
        sidebarList.appendChild(div);
    });
}

// 날짜 변경
function handleDateChange(selectedDateStr) {
    let existingIndex = allDiaries.findIndex(d => d.date === selectedDateStr);

    if (existingIndex !== -1) {
        currentIndex = existingIndex;
        updateCarouselPosition();
    } else {
        const newDiary = {
            id: 'temp-' + selectedDateStr,
            title: '',
            content: '',
            date: selectedDateStr,
            weather: '',
            emotion: '',
            recommended_url: ''
        };

        allDiaries.push(newDiary);
        allDiaries.sort((a, b) => a.date.localeCompare(b.date));

        currentIndex = allDiaries.findIndex(d => d.date === selectedDateStr);
        
        renderDiaryCarousel(); 
        showMessage(`${selectedDateStr}의 새 일기를 시작합니다.`);
    }
}

// 일기 카드 렌더링
function renderDiaryCarousel() {
    diaryCarousel.innerHTML = '';
    
    // 현재 인덱스의 일기만 표시
    if (allDiaries.length === 0) return;
    
    const it = allDiaries[currentIndex];
    const idx = currentIndex;
    
    const card = document.createElement('div');
    card.className = 'diary-card';
    card.dataset.index = idx;

    const isToday = it.date === new Date().toISOString().slice(0, 10);
    
    card.innerHTML = `
        <div class="controls">
            <div class="top-row">
                <div class="title-wrapper">
                    <input id="title-${idx}" type="text" placeholder="제목" value="${it.title || ''}" />
                </div>
                <input id="datePicker-${idx}" type="text" value="${it.date}" readonly />
                <div class="weather-picker" id="weatherPicker-${idx}">
                    <button class="weather-btn" data-value="sunny">☀️</button>
                    <button class="weather-btn" data-value="cloudy">☁️</button>
                    <button class="weather-btn" data-value="rain">🌧️</button>
                    <button class="weather-btn" data-value="snow">❄️</button>
                </div>
            </div>

            <textarea id="diary-${idx}" placeholder="오늘의 감정을 담아 일기를 써보세요.">${it.content || ''}</textarea>
            
            <div class="button-group-left">
                <button class="save-btn" data-index="${idx}">
                    ${isToday && it.id !== 'new' && !String(it.id).startsWith('temp-') 
                        ? '일기 수정'
                        : '일기 저장'}
                </button>
                <button class="recommend-btn" data-index="${idx}">음악 추천</button>
            </div>
        </div>
    `;
    
    diaryCarousel.appendChild(card);

    flatpickr(document.getElementById(`datePicker-${idx}`), { 
        dateFormat: 'Y-m-d', 
        defaultDate: it.date || new Date(),
        disableMobile: "true",
        allowInput: false, 
        onChange: function(selectedDates, dateStr) {
            if (dateStr && dateStr !== it.date) {
               handleDateChange(dateStr);
            }
        }
    });

    const weatherPickerEl = document.getElementById(`weatherPicker-${idx}`);
    if(it.weather) {
        const selectedBtn = weatherPickerEl.querySelector(`.weather-btn[data-value="${it.weather}"]`);
        if(selectedBtn) selectedBtn.classList.add('selected');
    }
    
    weatherPickerEl.onclick = e => {
        const btn = e.target.closest('.weather-btn');
        if (!btn) return;
        weatherPickerEl.querySelectorAll('.weather-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
    };

    document.querySelectorAll('.save-btn').forEach(btn => btn.onclick = handleSave);
    document.querySelectorAll('.recommend-btn').forEach(btn => btn.onclick = handleRecommend);
    
    // 현재 일기의 음악 추천 결과 표시
    updateMusicPanel();
}

// 음악 패널 업데이트
function updateMusicPanel() {
    const currentDiary = allDiaries[currentIndex];
    if (!currentDiary || !currentDiary.recommended_url) {
        musicContent.innerHTML = '<p class="music-placeholder">음악 추천 버튼을 눌러주세요</p>';
        return;
    }
    
    const url = currentDiary.recommended_url;
    const emotion = currentDiary.emotion || '';
    
    let html = `<strong style="display: block; margin-bottom: 15px; font-size: 16px; color: var(--primary);">${emotion ? `🎵 추천 음악 (${emotion})` : '🎵 추천 음악'}</strong>`;
    
    if (url.includes('youtube.com/watch')) {
        const embedUrl = url.replace('watch?v=', 'embed/');
        html += `<iframe src="${embedUrl}" allowfullscreen></iframe>`;
    }
    
    html += `<a href="${url}" target="_blank" style="display: block; margin-top: 15px; color: var(--primary); text-decoration: none; word-break: break-all;">${url.length > 50 ? url.substring(0, 50) + '...' : url}</a>`;
    
    musicContent.innerHTML = html;
}

// 캐러셀 이동 (현재는 단순히 일기만 다시 렌더링)
function updateCarouselPosition() {
    renderDiaryCarousel();
    updateSidebarList();
    updateMusicPanel(); // 음악 패널도 업데이트
}


// 데이터 가져오기
async function loadRecent() {
    try {
        const res = await fetch('/diary/list');
        const { items = [] } = await res.json();
        
        allDiaries = items;
        allDiaries.sort((a, b) => a.date.localeCompare(b.date));
        
        const today = new Date().toISOString().slice(0, 10);
        const exists = allDiaries.some(d => d.date === today);

        if (!exists) {
            allDiaries.push({
                id: 'new',
                title: '',
                content: '',
                date: today,
                weather: '',
                emotion: '',
                recommended_url: ''
            });
        }
        
        currentIndex = allDiaries.length - 1;
        renderDiaryCarousel();
        updateSidebarList();

    } catch (e) {
        console.error('일기 목록 로드 실패:', e);
        showMessage('일기 목록을 불러오지 못했습니다.');
    }
}

function getCurrentDiaryData(idx) {
    const cardEl = document.querySelector(`.diary-card[data-index="${idx}"]`);
    if (!cardEl) return null;

    const title = cardEl.querySelector(`#title-${idx}`).value.trim();
    const diary = cardEl.querySelector(`#diary-${idx}`).value.trim();
    const date = cardEl.querySelector(`#datePicker-${idx}`).value;
    
    const weatherBtn = cardEl.querySelector(`#weatherPicker-${idx} .weather-btn.selected`);
    const weather = weatherBtn ? weatherBtn.dataset.value : '';

    return { title, diary, date, weather };
}

// 저장
async function handleSave(e) {
    const idx = parseInt(e.target.dataset.index);
    const data = getCurrentDiaryData(idx);

    if (!data.diary) return showMessage('일기를 입력해주세요.');

    const button = e.target;
    button.disabled = true;
    button.textContent = '저장 중...';

    try {
        const res = await fetch('/mcp/recommend', { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...data, save: true, recommend: false }) 
        });

        if(!res.ok) throw new Error('서버 오류');

        await loadRecent();
        showMessage('일기가 저장되었습니다.');

    } catch (e) {
        console.error(e);
        showMessage('저장 실패! 서버 확인 필요');
    } finally {
        button.disabled = false;
        button.textContent = '일기 저장';
    }
}

// 음악 추천
async function handleRecommend(e) {
    const idx = parseInt(e.target.dataset.index);
    const data = getCurrentDiaryData(idx);

    if (!data.diary) return showMessage('일기를 먼저 입력하세요.');

    const button = e.target;
    button.disabled = true;
    button.textContent = '추천 중...';

    try {
        const res = await fetch('/mcp/recommend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...data, save: false, recommend: true }) 
        });
        
        const result = await res.json();

        const url = result.recommended_music_url;
        const emotion = result.emotion;
        
        if (url) {
            // 현재 일기 데이터 업데이트
            allDiaries[idx].recommended_url = url;
            allDiaries[idx].emotion = emotion;
            
            // 현재 인덱스와 일치하면 음악 패널 업데이트
            if (idx === currentIndex) {
                updateMusicPanel();
            }
            
            showMessage('추천 완료!');
        } else {
            showMessage('추천할 음악을 찾지 못했습니다.');
        }
        
    } catch (e) {
        console.error(e);
        showMessage('추천 실패! 서버 확인 필요');
    } finally {
        button.disabled = false;
        button.textContent = '음악 추천';
    }
}

// 일기 삭제
async function handleDelete(e) {
    const idx = parseInt(e.target.dataset.index);
    const diaryId = e.target.dataset.id;
    
    if (!confirm('정말 이 일기를 삭제하시겠습니까?')) {
        return;
    }
    
    try {
        const res = await fetch('/diary/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: parseInt(diaryId) })
        });
        
        if (!res.ok) throw new Error('서버 오류');
        
        await loadRecent();
        showMessage('일기가 삭제되었습니다.');
        
    } catch (e) {
        console.error(e);
        showMessage('삭제 실패! 서버 확인 필요');
    }
}

// 사이드바
bookmarkBtn.onclick = () => {
    sidebarPanel.classList.add('show');
};
closeSidebar.onclick = () => {
    sidebarPanel.classList.remove('show');
};

// 설정 패널
settingsBtn.onclick = () => settingsPanel.classList.toggle('show');

saveUserName.onclick = () => {
    const name = userNameInput.value.trim();
    if (name) {
        headerText.textContent = `${name}님의 MOODIARY`;
        localStorage.setItem('userName', name);
    } else {
        headerText.textContent = `MOODIARY`;
        localStorage.removeItem('userName');
    }
    settingsPanel.classList.remove('show');
};

// 초기 실행
(function init() {
    const savedName = localStorage.getItem('userName');
    if (savedName) {
        userNameInput.value = savedName;
        headerText.textContent = `${savedName}님의 MOODIARY`; 
    }
    loadRecent();
})();

window.addEventListener('resize', updateCarouselPosition);
