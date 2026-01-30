import unittest
from unittest.mock import Mock, patch, MagicMock
import time
from api.komga_api import KomgaApi


class TestKomgaApiReplaceCollection(unittest.TestCase):
    """测试 KomgaApi 的 replace_collection 方法"""

    def setUp(self):
        """设置测试环境"""
        # Mock the authentication to avoid actual API calls
        with patch('api.komga_api.requests.Session') as mock_session:
            mock_session_instance = MagicMock()
            mock_session.return_value = mock_session_instance
            
            # Mock the login response
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_session_instance.get.return_value = mock_response
            
            self.api = KomgaApi(
                base_url="http://localhost:25600",
                username="test",
                password="test"
            )
            self.api.r = mock_session_instance

    def test_replace_collection_when_collection_not_exists(self):
        """测试替换不存在的收藏 - 应该直接创建"""
        # Mock get_collection_id_by_search_name to return None (collection doesn't exist)
        self.api.get_collection_id_by_search_name = Mock(return_value=None)
        
        # Mock add_collection to return True
        self.api.add_collection = Mock(return_value=True)
        
        # Call replace_collection
        result = self.api.replace_collection("TestCollection", False, ["series1", "series2"])
        
        # Verify behavior
        self.api.get_collection_id_by_search_name.assert_called_once_with("TestCollection")
        self.api.add_collection.assert_called_once_with("TestCollection", False, ["series1", "series2"])
        self.assertTrue(result)

    def test_replace_collection_when_deletion_succeeds(self):
        """测试替换现有收藏且删除成功 - 应该删除后等待并创建新的"""
        # Mock get_collection_id_by_search_name to return an ID
        self.api.get_collection_id_by_search_name = Mock(return_value="collection123")
        
        # Mock delete_collection to return True (success)
        self.api.delete_collection = Mock(return_value=True)
        
        # Mock add_collection to return True
        self.api.add_collection = Mock(return_value=True)
        
        # Measure time to verify sleep is called
        start_time = time.time()
        result = self.api.replace_collection("TestCollection", False, ["series1", "series2"])
        elapsed_time = time.time() - start_time
        
        # Verify behavior
        self.api.get_collection_id_by_search_name.assert_called_once_with("TestCollection")
        self.api.delete_collection.assert_called_once_with("collection123")
        self.api.add_collection.assert_called_once_with("TestCollection", False, ["series1", "series2"])
        self.assertTrue(result)
        
        # Verify that sleep was called (elapsed time should be at least 0.5 seconds)
        self.assertGreaterEqual(elapsed_time, 0.5)

    def test_replace_collection_when_deletion_fails(self):
        """测试替换现有收藏但删除失败 - 应该返回 False 且不创建新的"""
        # Mock get_collection_id_by_search_name to return an ID
        self.api.get_collection_id_by_search_name = Mock(return_value="collection123")
        
        # Mock delete_collection to return False (failure)
        self.api.delete_collection = Mock(return_value=False)
        
        # Mock add_collection (should not be called)
        self.api.add_collection = Mock(return_value=True)
        
        # Call replace_collection
        result = self.api.replace_collection("TestCollection", False, ["series1", "series2"])
        
        # Verify behavior
        self.api.get_collection_id_by_search_name.assert_called_once_with("TestCollection")
        self.api.delete_collection.assert_called_once_with("collection123")
        self.api.add_collection.assert_not_called()  # Should NOT be called
        self.assertFalse(result)

    def test_replace_collection_preserves_parameters(self):
        """测试替换收藏时正确传递参数"""
        # Mock get_collection_id_by_search_name to return None
        self.api.get_collection_id_by_search_name = Mock(return_value=None)
        
        # Mock add_collection to capture parameters
        self.api.add_collection = Mock(return_value=True)
        
        # Call with specific parameters
        collection_name = "特殊收藏"
        ordered = True
        series_ids = ["id1", "id2", "id3"]
        
        self.api.replace_collection(collection_name, ordered, series_ids)
        
        # Verify parameters are passed correctly
        self.api.add_collection.assert_called_once_with(collection_name, ordered, series_ids)


if __name__ == '__main__':
    unittest.main()
