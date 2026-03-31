class GitHubCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---- /git-create ----
    @app_commands.command(
        name='git-create',
        description='Create a new file in a GitHub repository'
    )
    @app_commands.autocomplete(repository=get_user_repos)
    async def git_create(
        self,
        interaction: discord.Interaction,
        repository: str,  # Dropdown from your repos
        path: str,        # Example: folder1/hello.txt
        content: str,     # Text you want inside the file
        commit_message: str = None  # Optional
    ):
        """
        repository: pick your repository from a dropdown.
        path: path + filename (like folder/file.txt) where you want the file.
        content: what you want inside the file.
        commit_message: message to describe this change (optional).
        """
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id != YOUR_USER_ID:
            await interaction.followup.send("❌ You don't have permission.", ephemeral=True)
            return

        if not commit_message:
            commit_message = f'Create {path} via bot'

        payload = {
            'message': commit_message,
            'content': base64.b64encode(content.encode()).decode(),
        }

        result, error = await github_request(f'repos/{repository}/contents/{path}', 'PUT', payload)
        if error:
            await interaction.followup.send(f'❌ Could not create file: {error}', ephemeral=True)
        else:
            await interaction.followup.send(f'✅ File `{path}` created in `{repository}`!', ephemeral=True)

    # ---- /git-edit ----
    @app_commands.command(
        name='git-edit',
        description='Edit an existing file in a GitHub repository'
    )
    @app_commands.autocomplete(repository=get_user_repos)
    async def git_edit(
        self,
        interaction: discord.Interaction,
        repository: str,    # Pick from dropdown
        path: str,          # Pick file path, can autocomplete later
        content: str,       # New content for the file
        commit_message: str = None  # Optional
    ):
        """
        repository: pick your repository from dropdown
        path: file you want to update
        content: new text/code for the file
        commit_message: optional description
        """
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id != YOUR_USER_ID:
            await interaction.followup.send("❌ You don't have permission.", ephemeral=True)
            return

        # Get the current SHA automatically
        file_info, error = await github_request(f'repos/{repository}/contents/{path}')
        if error:
            await interaction.followup.send(f'❌ Could not fetch file: {error}', ephemeral=True)
            return
        sha = file_info.get('sha')
        if not sha:
            await interaction.followup.send('❌ Could not get file SHA.', ephemeral=True)
            return

        if not commit_message:
            commit_message = f'Update {path} via bot'

        payload = {
            'message': commit_message,
            'content': base64.b64encode(content.encode()).decode(),
            'sha': sha
        }

        result, error = await github_request(f'repos/{repository}/contents/{path}', 'PUT', payload)
        if error:
            await interaction.followup.send(f'❌ Could not update file: {error}', ephemeral=True)
        else:
            await interaction.followup.send(f'✅ File `{path}` updated in `{repository}`!', ephemeral=True)

    # ---- /git-delete ----
    @app_commands.command(
        name='git-delete',
        description='Delete a file from a GitHub repository'
    )
    @app_commands.autocomplete(repository=get_user_repos)
    async def git_delete(
        self,
        interaction: discord.Interaction,
        repository: str,
        path: str,
        commit_message: str = None
    ):
        """
        repository: pick repo from dropdown
        path: file you want to delete
        commit_message: optional description
        """
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id != YOUR_USER_ID:
            await interaction.followup.send("❌ You don't have permission.", ephemeral=True)
            return

        # Automatically get SHA
        file_info, error = await github_request(f'repos/{repository}/contents/{path}')
        if error:
            await interaction.followup.send(f'❌ Could not fetch file: {error}', ephemeral=True)
            return
        sha = file_info.get('sha')
        if not sha:
            await interaction.followup.send('❌ Could not get file SHA.', ephemeral=True)
            return

        if not commit_message:
            commit_message = f'Delete {path} via bot'

        payload = {
            'message': commit_message,
            'sha': sha
        }
        result, error = await github_request(f'repos/{repository}/contents/{path}', 'DELETE', payload)
        if error:
            await interaction.followup.send(f'❌ Could not delete file: {error}', ephemeral=True)
        else:
            await interaction.followup.send(f'✅ File `{path}` deleted from `{repository}`!', ephemeral=True)
