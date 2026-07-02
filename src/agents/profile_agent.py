class ProfileAgent:
    def __init__(self, profile_store, admin_reply_handler):
        self.profile_store = profile_store
        self.admin_reply_handler = admin_reply_handler

    async def get_profile_info(self, update, context, question: str):
        answer = self.profile_store.find_answer(question)

        if answer:
            return {
                "status": "answered",
                "answer": answer,
            }

        await self.admin_reply_handler.notify_admin(
            update=update,
            context=context,
            question=question,
        )

        return {
            "status": "pending",
            "answer": "Je ne connais pas encore la réponse. J’ai demandé à Malo.",
        }