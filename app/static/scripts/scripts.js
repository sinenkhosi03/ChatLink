const db = new Dexie("ChatLinkDB");

db.version(1).stores({
    chat_history:"friend"
});

document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    socket.on('new_message', (data) => {
        receivedMsgDisplayer(data.chat_name, data.message);
    });
});

async function messageDisplay(){
    let input = document.querySelector("#message-input");
    let messageDisplayer = document.querySelector(".messages-container");
    const chat_name = messageDisplayer.dataset.friend;
    let file = document.querySelector("#file-upload")
   
    console.log(chat_name)

    console.log("Welcome to chatlink");
    const message = input.value;

    if(message.trim() === "") return;

    const date_time = new Date().toISOString();

    let msgCont = document.createElement("div");

    msgCont.className = "send-message";
    msgCont.innerHTML = `
                <div class="chat-box">
                    <p>
                    ${message}
                    </p>
                </div>
    `;
    
    newMsg = await buildMsg("me", message, date_time);
    await saveMessage(chat_name, newMsg);


    messageDisplayer.appendChild(msgCont);
    console.log(message);

    input.value = "";

    await fetch("/send_message", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            friend: `${chat_name}`,
            message: `${message}`
        })
    });
}

//for receiving msg
async function receivedMsgDisplay(chat_name, message){
    let messageDisplayer = document.querySelector(".messages-container");
    const date_time = new Date().toISOString();
    
    let msgCont = document.createElement("div");
    msgCont.className = "recieve-message";
    msgCont.innerHTML = `
                <h5>${chat_name}</h5>
                    <p>
                    ${message}
                    </p>
    `;
    console.log("came here")

    const newMsg = await buildMsg("them", message, date_time);
    await saveMessage(chat_name, newMsg);

    messageDisplayer.appendChild(msgCont);
    console.log(message);
}

async function openChat(chat_name) {
    const messageDisplayer = document.querySelector(".messages-container");
    messageDisplayer.dataset.friend = friendName;
    const messages = await loadChat(chat_name);
    messageDisplayer.innerHTML = ""; // clear current display

    messages.forEach(msg => {
        let msgCont = document.createElement("div");
        msgCont.className = msg.sender === "me" ? "sent-message" : "received-message";
        msgCont.innerHTML = `
            <div class="chat-box">
                ${msg.sender === "them" ? `<h5>${chat_name}</h5>` : ""}
                <p>${msg.message}</p>
                <small>${msg.date_time}</small>
            </div>
        `;
        messageDisplayer.appendChild(msgCont);
    });
}


//save msg
async function saveMessage(friendName, newMsg){
    const record = await db.chat_history.get(friendName) || {friend:friendName, messages: []};

    record.messages.push(newMsg);
    await db.chat_history.put(record);
}

// load chat
async function loadChat(friendName){
    const record = await db.chat_history.get(friendName);
    return record?.messages || [];
}

function buildMsg(sender, message, date_time){
    return { sender, message, date_time };
}

const urlParams = new URLSearchParams(window.location.search);
const chat_name = urlParams.get('friend'); 

if (chat_name) { 
    document.querySelector('.messages-container').dataset.friend = chat_name;
    console.log(chat_name);
    openChat(chat_name);
}